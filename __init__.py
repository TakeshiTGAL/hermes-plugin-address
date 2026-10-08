"""jp-address: one tool, address_split. No hooks, slash command, CLI, or cron."""


def register(ctx) -> None:
    if __package__:
        from .address import register as register_tool
    else:
        from address import register as register_tool

    register_tool(ctx)
