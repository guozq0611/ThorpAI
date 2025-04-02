import { useTranslation } from 'react-i18next';
import { useEffect, useState } from 'react';
import { Locale } from 'date-fns';
import { ar, enUS, es } from 'date-fns/locale';

export default function useLocale() {
	const { i18n } = useTranslation();

	const findLocale: Locale =
		[enUS, es, ar].find((key) => key.code && key.code.includes(i18n.language)) || enUS;

	const [activeLocale, setActiveLocale] = useState<Locale>(findLocale);

	useEffect(() => {
		setActiveLocale(findLocale);
	}, [findLocale, i18n.language]);

	return activeLocale;
}
