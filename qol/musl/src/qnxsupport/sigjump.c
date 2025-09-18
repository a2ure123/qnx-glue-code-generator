#include <setjmp.h>

void __sigjmp_prolog(sigjmp_buf env, int msk)
{
    // this function is just a prolog
    //
    // Without its implementation,
    // some programs still work.
}
