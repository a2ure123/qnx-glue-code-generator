#include <stdarg.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FLAG_ABORT_ON_OVERFLOW 1
#define FLAG_TERMINATE 2

int __vsprintf_chk(char *str, int flag, size_t os, const char *format, va_list ap);

int __sprintf_chk(char *str, int flag, size_t os, const char *format, ...) {
    va_list ap;
    va_start(ap, format);
    int ret = __vsprintf_chk(str, flag, os, format, ap);
    va_end(ap);
    return ret;
}

int __vsprintf_chk(char *str, int flag, size_t os, const char *format, va_list ap) {
    size_t buf_size = os;
    int ret = vsnprintf(str, buf_size, format, ap);
    
    if (ret >= (int)buf_size) {
        if (flag & FLAG_ABORT_ON_OVERFLOW) {
            abort();
        } else {
            str[buf_size-1] = '\0';
        }
    }
    return ret;
}

int __snprintf_chk(char *str, size_t size, int flag, size_t os, const char *format, ...) {
    va_list ap;
    va_start(ap, format);
    int ret = vsnprintf(str, size, format, ap);
    va_end(ap);

    if (ret < 0) {
        str[0] = '\0';
        abort();
    } else if ((size_t)ret >= size) {
        if (flag & FLAG_TERMINATE) {
            str[size-1] = '\0';
        } else {
            abort();
        }
    }
    return ret;
}