#include <stdarg.h>
#include <stdio.h>

int slogf(int code, int severity, const char *fmt, ...)
{
	int ret;
	va_list ap;

	printf("SLOG [%d] [%d] ", code, severity);
	va_start(ap, fmt);
	ret = vprintf(fmt, ap);
	va_end(ap);
	putchar('\n');

	return ret;
}
