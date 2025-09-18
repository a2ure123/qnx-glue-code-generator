#include <locale.h>

struct qnx_lconv
	{	/* locale-specific information */
		/* controlled by LC_MONETARY */
	char *currency_symbol;
	char *int_curr_symbol;
	char *mon_decimal_point;
	char *mon_grouping;
	char *mon_thousands_sep;
	char *negative_sign;
	char *positive_sign;
	char frac_digits;
	char int_frac_digits;
	char n_cs_precedes;
	char n_sep_by_space;
	char n_sign_posn;
	char p_cs_precedes;
	char p_sep_by_space;
	char p_sign_posn;

	char int_n_cs_precedes;	/* Added with C99 */
	char int_n_sep_by_space;	/* Added with C99 */
	char int_n_sign_posn;		/* Added with C99 */
	char int_p_cs_precedes;	/* Added with C99 */
	char int_p_sep_by_space;	/* Added with C99 */
	char int_p_sign_posn;		/* Added with C99 */

		/* controlled by LC_NUMERIC */
	char *decimal_point;
	char *grouping;
	char *thousands_sep;
	char *_Frac_grouping;
	char *_Frac_sep;
	char *_False;
	char *_True;

		/* controlled by LC_MESSAGES */
	char *_No;
	char *_Yes;
	char *_Nostr;
	char *_Yesstr;
	char *_Reserved[8];
	};

void convert_musl_to_qnx_lconv(const struct lconv *musl, struct qnx_lconv *qnx) {
    qnx->decimal_point = musl->decimal_point;
    qnx->thousands_sep = musl->thousands_sep;
    qnx->grouping = musl->grouping;

    qnx->currency_symbol = musl->currency_symbol;
    qnx->int_curr_symbol = musl->int_curr_symbol;
    qnx->mon_decimal_point = musl->mon_decimal_point;
    qnx->mon_thousands_sep = musl->mon_thousands_sep;
    qnx->mon_grouping = musl->mon_grouping;
    qnx->positive_sign = musl->positive_sign;
    qnx->negative_sign = musl->negative_sign;

    qnx->frac_digits = musl->frac_digits;
    qnx->int_frac_digits = musl->int_frac_digits;

    qnx->p_cs_precedes = musl->p_cs_precedes;
    qnx->p_sep_by_space = musl->p_sep_by_space;
    qnx->p_sign_posn = musl->p_sign_posn;
    qnx->n_cs_precedes = musl->n_cs_precedes;
    qnx->n_sep_by_space = musl->n_sep_by_space;
    qnx->n_sign_posn = musl->n_sign_posn;

    qnx->int_p_cs_precedes = musl->int_p_cs_precedes;
    qnx->int_p_sep_by_space = musl->int_p_sep_by_space;
    qnx->int_p_sign_posn = musl->int_p_sign_posn;
    qnx->int_n_cs_precedes = musl->int_n_cs_precedes;
    qnx->int_n_sep_by_space = musl->int_n_sep_by_space;
    qnx->int_n_sign_posn = musl->int_n_sign_posn;

    qnx->_Frac_grouping = NULL;
    qnx->_Frac_sep = NULL;
    qnx->_False = NULL;
    qnx->_True = NULL;

    qnx->_No = NULL;
    qnx->_Yes = NULL;
    qnx->_Nostr = NULL;
    qnx->_Yesstr = NULL;

    for (int i = 0; i < 8; i++) {
        qnx->_Reserved[i] = NULL;
    }
}

struct qnx_lconv *_qnx_localeconv(void) {
    static struct qnx_lconv qnx_lconv;
    static int initialized = 0;

    if (!initialized) {
        const struct lconv *musl_lconv = localeconv();
        convert_musl_to_qnx_lconv(musl_lconv, &qnx_lconv);
        initialized = 1;
    }

    return &qnx_lconv;
}