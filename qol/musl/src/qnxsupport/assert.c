#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

char *utoa(unsigned n, char *s, int base);

void __assert(const char *expr, const char *file, unsigned line,
	      const char *func)
{
	int fd = fileno(stderr);
	char lbuf[10];

	if (utoa(line, lbuf, 10) == NULL) {
		lbuf[0] = '?';
		lbuf[1] = '\0';
	}

	if (func) {
		write(fd, "In function ", 12);
		write(fd, func, strlen(func));
		write(fd, " -- ", 4);
	}

	write(fd, file, strlen(file));
	write(fd, ":", 1);
	write(fd, lbuf, strlen(lbuf));
	write(fd, " ", 1);
	write(fd, expr, strlen(expr));
	write(fd, " -- assertion failed\n", 21);
	abort();
}
