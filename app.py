import mimetypes
import os.path
import pathlib
from contextlib import asynccontextmanager, contextmanager
from functools import partial
from typing import Annotated, Literal, TypeAlias, TypedDict, cast
from urllib.parse import quote

import fsspec
import uvicorn
from fastapi import Depends, FastAPI, Path, Request, Response
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DEBUG: bool = Field(default=False)

    PROTOCOL: str = Field(default="file")
    DOCUMENT_ROOT: str = Field(default="file://")

    CSS_LINE_HIGHT: str = Field(default="1.5")
    CSS_MAX_WIDTH: str = Field(default="80%")
    CSS_FONT_FAMILY: str = Field(default="serif")

    FOOTER_MESSAGE: str = Field(
        default="""
        Powered by <a target="_blank" href="https://github.com/jblawatt/fsspec-browser">fsspec-browser</a>
        """
    )

    IGNORE_PATTERNS: list[str] = Field(default=[])
    IGNORE_FILE: str = Field(default=".fsspecignore")

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


class PathStepDict(TypedDict):
    name: str
    href: str


class DirInfoDict(TypedDict):
    name: str
    type: Literal["directory", "file"]


class DirInfoContextItem(DirInfoDict, total=False):
    url: str
    dirname: str


ResponseFormats: TypeAlias = Literal["html", "json"]


def dep_fs() -> fsspec.AbstractFileSystem:
    return fsspec.filesystem(settings.PROTOCOL)


_IGNORE_PATTERN = []


@asynccontextmanager
async def _build_ignore_pattern(_: FastAPI):
    all_patterns = set()
    for pattern in settings.IGNORE_PATTERNS:
        all_patterns.add(pattern)
    ignore_file = pathlib.Path(settings.IGNORE_FILE)
    if ignore_file.exists():
        for pattern in ignore_file.read_text().split("\n"):
            pattern = pattern.strip()
            if pattern.startswith("#"):
                continue
            all_patterns.add(pattern)
    _IGNORE_PATTERN.extend(filter(None, all_patterns))
    yield
    _IGNORE_PATTERN.clear()


app = FastAPI(debug=settings.DEBUG, lifespan=_build_ignore_pattern)


@app.get("/")
async def index_root_view(
    request: Request,
    fs: Annotated[fsspec.AbstractFileSystem, Depends(dep_fs)],
    format: ResponseFormats = "html",
) -> Response:
    return index_view_plain("", request, fs, format)


@app.get("/{path:path}")
async def index_path_view(
    path: Annotated[str, Path(..., description="...")],
    request: Request,
    fs: Annotated[fsspec.AbstractFileSystem, Depends(dep_fs)],
    format: ResponseFormats = "html",
) -> Response:
    if path.endswith("favicon.ico"):
        return Response(status_code=404)
    return index_view_plain(path, request, fs, format)


def index_view_plain(
    path: str,
    request: Request,
    fs: fsspec.AbstractFileSystem,
    format: ResponseFormats,
) -> Response:
    path = path.strip(fs.sep)
    current_path = os.path.join(settings.DOCUMENT_ROOT, path)

    if not fs.exists(current_path):
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "path": path,
                "ascii_404": ASCII_404,
            },
        )

    if fs.isfile(current_path):
        mtype, _ = mimetypes.guess_type(current_path)
        return Response(
            content=fs.read_bytes(current_path),
            media_type=mtype,
        )

    ls_items: list[DirInfoDict] = fs.ls(current_path, detail=True)
    ls_items = filter(lambda o: not matches_pattern(o["name"]), ls_items)
    ls_items = sorted(ls_items, key=lambda o: (o["type"], o["name"]))

    items = list(
        map(
            partial(
                to_dir_info_context_item,
                path=path,
                sep=fs.sep,
            ),
            ls_items,
        )
    )

    parent_path = quote(fs.sep + os.path.dirname(path).strip(fs.sep))

    is_root = current_path.strip(fs.sep) == settings.DOCUMENT_ROOT.strip(fs.sep)

    context = {
        "is_root": is_root,
        "path": fs.sep + path,
        "path_links": build_path_links(path.split("/")),
        "parent": parent_path,
        "items": items,
        "dirs_count": count_items_by_key_value(
            ls_items,
            "type",
            "directory",
        ),
        "files_count": count_items_by_key_value(
            ls_items,
            "type",
            "file",
        ),
    }

    if format == "json":
        return JSONResponse(context)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={**context, "settings": settings},
    )


def count_items_by_key_value(items: list[DirInfoDict], key: str, value: str) -> int:
    return len(list(filter(lambda o: o[key] == value, items)))


def build_path_links(parts: list[str]) -> list[PathStepDict]:
    if not parts:
        return []
    if len(parts) == 1:
        full = []
        last = parts[0]
    else:
        *full, last = parts
    return build_path_links(full) + [
        {
            "name": last,
            "href": quote("/" + "/".join(full + [last])),
        }
    ]


def to_dir_info_context_item(
    item: DirInfoDict, path: str, sep: str
) -> DirInfoContextItem:
    basename = os.path.basename(item["name"])
    dirname = os.path.dirname(item["name"])
    # split the full path and urlencode the parts then
    # combine them back together by using the seperator
    url = sep + sep.join(filter(None, path.split(sep) + [basename]))
    # there is not option to add extra items to typeddict
    # so we cast it to typed dict but leave extra values.
    return cast(
        DirInfoContextItem,
        {
            **item,
            "name": basename,
            "url": quote(url),
            "dirname": dirname,
        },
    )


def matches_pattern(value: str) -> bool:
    for p in _IGNORE_PATTERN:
        if pathlib.PurePath(value).match(p):
            return True
    return False


if __name__ == "__main__":
    uvicorn.run(app)
