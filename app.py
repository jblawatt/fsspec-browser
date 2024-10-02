import functools
import mimetypes
import os.path
from typing import Annotated, Any, TypedDict, cast
from urllib.parse import quote

import fsspec
import uvicorn
from fastapi import Depends, FastAPI, Path, Request, Response
from fastapi.templating import Jinja2Templates
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DEBUG: bool = Field(default=False)

    PROTOCOL: str = Field(default="file")
    DOCUMENT_ROOT: str = Field(default="file://")

    model_config = SettingsConfigDict(
        env_prefix="fsspec_browser_",
    )


settings = Settings()  # noqa
templates = Jinja2Templates("templates")

ASCII_404 = r"""
   _____  _______      _____
  /  |  | \   _  \    /  |  |
 /   |  |_/  /_\  \  /   |  |_
/    ^   /\  \_/   \/    ^   /
\____   |  \_____  /\____   |
     |__|        \/      |__|
"""


def dep_fs() -> fsspec.AbstractFileSystem:
    return fsspec.filesystem(settings.PROTOCOL)


app = FastAPI(debug=settings.DEBUG)


class ItemDict(TypedDict, total=False):
    name: str
    url: str
    dirname: str


def to_context_item(path: str, item: dict[str, Any], sep: str) -> ItemDict:
    basename = os.path.basename(item["name"])
    dirname = os.path.dirname(item["name"])
    # split the full path and urlencode the parts then
    # combine them back together by using the seperator
    url = sep + sep.join(filter(None, path.split(sep) + [basename]))
    # there is not option to add extra items to typeddict
    # so we cast it to typed dict but leave extra values.
    return cast(
        ItemDict,
        {
            **item,
            "name": basename,
            "url": quote(url),
            "dirname": dirname,
        },
    )


@app.get("/")
async def index_root_view(
    request: Request,
    fs: Annotated[fsspec.AbstractFileSystem, Depends(dep_fs)],
) -> Response:
    return index_view_plain("", request, fs)


@app.get("/{path:path}")
async def index_path_view(
    path: Annotated[str, Path(..., description="...")],
    request: Request,
    fs: Annotated[fsspec.AbstractFileSystem, Depends(dep_fs)],
) -> Response:
    if path.endswith("favicon.ico"):
        return Response(status_code=404)
    return index_view_plain(path, request, fs)


def index_view_plain(
    path: str,
    request: Request,
    fs: fsspec.AbstractFileSystem,
) -> Response:
    path = path.strip(".")
    path = path.strip(fs.sep)
    current_path = os.path.join(settings.DOCUMENT_ROOT, path)

    if not fs.exists(current_path):
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"path": path, "ascii_404": ASCII_404},
        )

    if fs.isfile(current_path):
        mtype, _ = mimetypes.guess_type(current_path)
        return Response(
            content=fs.read_bytes(current_path),
            media_type=mtype,
        )

    items = fs.ls(current_path, detail=True)
    items = map(functools.partial(to_context_item, path, sep=fs.sep), items)
    items = sorted(items, key=lambda o: (o["type"], o["name"]))
    parent = quote(fs.sep + os.path.dirname(path).strip(fs.sep))

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "is_root": current_path.strip(fs.sep)
            == settings.DOCUMENT_ROOT.strip(fs.sep),
            "path": fs.sep + path,
            "parent": parent,
            "items": items,
        },
    )


if __name__ == "__main__":
    uvicorn.run(app)
