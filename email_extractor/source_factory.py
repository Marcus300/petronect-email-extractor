"""Select the email backend without coupling the UI to an implementation."""

from collections.abc import Callable


GRAPH_SOURCE = "graph"
CLASSIC_SOURCE = "classic"
EMAIL_SOURCE_MODE = GRAPH_SOURCE


def create_email_source(
    on_authentication: Callable[[dict], None] | None = None,
    parent_window_handle: int | None = None,
    mode: str | None = None,
):
    selected_mode = mode or EMAIL_SOURCE_MODE
    if selected_mode == GRAPH_SOURCE:
        from .graph import GraphEmailSource

        return GraphEmailSource(
            on_authentication=on_authentication,
            parent_window_handle=parent_window_handle,
        )
    if selected_mode == CLASSIC_SOURCE:
        from .outlook import OutlookEmailSource

        return OutlookEmailSource()
    raise RuntimeError(f"Modo de fonte de e-mail inválido: {selected_mode}")
