import gettext
from pathlib import Path

script_dir = Path(__file__).resolve().parent
locale_dir = script_dir / "locale"


def setup_i18n():
    translate = gettext.translation("workflow", locale_dir, fallback=True)
    gettext.bindtextdomain("workflow", locale_dir)
    gettext.textdomain("workflow")
    return translate.gettext


_ = setup_i18n()
