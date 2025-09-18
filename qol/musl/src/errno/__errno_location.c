// #include <errno.h>
// #include "pthread_impl.h"
#include <features.h>

int errno;

int *__errno_location(void)
{
	// return &__pthread_self()->errno_val;
	return &errno;
}

weak_alias(__errno_location, ___errno_location);
