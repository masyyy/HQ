import pyfiglet


def get_banner(compact: bool = False) -> str:
    if compact:
        return pyfiglet.figlet_format("HQ", font="small") + "company os\n"
    return pyfiglet.figlet_format("HQ", font="ansi_shadow") + "  company os\n"
