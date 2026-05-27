from services.management.commands.check_media_files import Command as CheckMediaFilesCommand


class Command(CheckMediaFilesCommand):
    help = "Alias for check_media_files."
