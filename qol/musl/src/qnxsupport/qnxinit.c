#include "libc.h"
#include "locale_impl.h"
#include "stdio.h"
#include <stddef.h>

void _init_libc(int argc, char *argv[], char *arge[], void *auxv,
		void (*exit_func)(void))
{
	__init_libc(arge, argv[0]);

	void (*f)(void) = __libc_start_init;
	__asm__ ( "" : "+r"(f) : : "memory" );
	f();

	CURRENT_LOCALE = C_LOCALE;
}

void _preinit_array(void (**start)(void), void (**end)(void))
{
	void (**f)(void);
	for (f = start; f < end; f++) {
		(*f)();
	}
}

void _init_array(void (**start)(void), void (**end)(void))
{
	// printf("init_array: start %p, end %p\n", start, end);
	// void (**f)(void);
	// for (f = start; f < end; f++) {
	// 	(*f)();
	// }
}
void _fini_array(void (**start)(void), void (**end)(void))
{
	// printf("fini_array: start %p, end %p\n", start, end);
	// void (**f)(void);
	// for (f = start; f < end; f++) {
	// 	atexit(*f);
	// }
}

int *__get_errno_ptr(void)
{
	return &errno;
}

int tcgetsize(int filedes, int *prows, int *pcols)
{
	if (prows != NULL)
		*prows = 24;
	if (pcols != NULL)
		*pcols = 80;
	return 0;
}
