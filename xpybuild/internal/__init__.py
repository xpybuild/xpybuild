# need to get this here before we set sys.stdout=None
import locale, sys
DEFAULT_PROCESS_ENCODING = sys.stdout.encoding or locale.getpreferredencoding()
