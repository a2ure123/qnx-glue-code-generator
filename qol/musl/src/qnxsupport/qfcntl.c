#include "syscall.h"
#include <stdarg.h>
#include <fcntl.h>

#define QNX_O_RDONLY 000000 /*  Read-only mode  */
#define QNX_O_WRONLY 000001 /*  Write-only mode */
#define QNX_O_RDWR 000002 /*  Read-Write mode */
#define QNX_O_NONBLOCK 000200 /*  Non-blocking I/O                */
#define QNX_O_APPEND 000010 /*  Append (writes guaranteed at the end)   */
#define QNX_O_DSYNC 000020 /*  Data integrity synch    */
#define QNX_O_RSYNC 000100 /*  Data integrity synch    */
#define QNX_O_SYNC 000040 /*  File integrity synch    */
#define QNX_O_CREAT 000400 /*  Opens with file create      */
#define QNX_O_TRUNC 001000 /*  Open with truncation        */
#define QNX_O_EXCL 002000 /*  Exclusive open          */
#define QNX_O_NOCTTY 004000 /*  Don't assign a controlling terminal */

static int qnx_flag_to_linux(mode_t f)
{
	int ret = 0;

#define CONV_MODE(n)       \
	if (f & QNX_O_##n) \
	ret |= O_##n

	CONV_MODE(RDONLY);
	CONV_MODE(WRONLY);
	CONV_MODE(RDONLY);
	CONV_MODE(WRONLY);
	CONV_MODE(RDWR);
	CONV_MODE(NONBLOCK);
	CONV_MODE(APPEND);
	CONV_MODE(DSYNC);
	CONV_MODE(RSYNC);
	CONV_MODE(SYNC);
	CONV_MODE(CREAT);
	CONV_MODE(TRUNC);
	CONV_MODE(EXCL);
	CONV_MODE(NOCTTY);

#undef CONV_MODE

	return ret;
}

int _qnx_open(const char *filename, int flags, ...)
{
	mode_t mode = 0;

	va_list ap;
	va_start(ap, flags);
	mode = va_arg(ap, mode_t);
	va_end(ap);
	flags = qnx_flag_to_linux(flags);
	return open(filename, flags, mode);
}

int _qnx_openat(int dirfd, const char *filename, int flags, ...)
{
    mode_t mode = 0;

    va_list ap;
    va_start(ap, flags);
    mode = va_arg(ap, mode_t);
    va_end(ap);
    flags = qnx_flag_to_linux(flags);
    return openat(dirfd, filename, flags, mode);
}

int _qnx_creat(const char *filename, mode_t mode)
{
    return creat(filename, mode);
}

