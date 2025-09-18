char *itoa(int n, char *s, int base)
{
	int i, sign;
	if ((sign = n) < 0)
		n = -n;
	i = 0;
	do {
		s[i++] = n % base + '0';
	} while ((n /= base) > 0);
	if (sign < 0)
		s[i++] = '-';
	s[i] = '\0';
	return s;
}

char *utoa(unsigned n, char *s, int base)
{
	int i;
	i = 0;
	do {
		s[i++] = n % base + '0';
	} while ((n /= base) > 0);
	s[i] = '\0';
	return s;
}
