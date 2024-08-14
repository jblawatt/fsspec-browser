import functools
import mimetypes
import os.path
from typing import Annotated

import fsspec
from fastapi import Depends, FastAPI, Path, Request, Response
from fastapi.templating import Jinja2Templates
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    DEBUG: bool = Field(default=False)

    PROTOCOL: str = Field()
    DOCUMENT_ROOT: str = Field()

    model_config = SettingsConfigDict(
        env_prefix="fsspec_browser_",
    )


settings = Settings()
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


def to_context_item(path: str, item: dict):
    basename = os.path.basename(item["name"])
    dirname = os.path.dirname(item["name"])
    url = "/" + "/".join(filter(None, [path, basename]))
    return {
        **item,
        "name": basename,
        "url": url,
        "dirname": dirname,
    }


@app.get("/")
async def index_root_view(
    request: Request,
    fs: Annotated[fsspec.AbstractFileSystem, Depends(dep_fs)],
):
    return index_view_plain("", request, fs)


@app.get("/{path:path}")
async def index_path_view(
    path: Annotated[str, Path(..., description="...")],
    request: Request,
    fs: Annotated[fsspec.AbstractFileSystem, Depends(dep_fs)],
):
    if path.endswith("favicon.ico"):
        return None
    return index_view_plain(path, request, fs)


def index_view_plain(path, request, fs: fsspec.AbstractFileSystem):
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
    items = map(functools.partial(to_context_item, path), items)
    items = sorted(items, key=lambda o: (o["type"], o["name"]))
    parent = "/" + os.path.dirname(path)

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
