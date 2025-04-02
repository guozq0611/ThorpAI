import React from 'react';
import ReactDateRangeClient from '@/app/[locale]/integrated/react-date-range/client';
import TranslationsProvider from '@/components/TranslationsProvider';

const i18nNamespaces = ['translation'];

const ReactDateRangePage = ({ params: { locale } }: { params: { locale: string } }) => {
	return (
		<TranslationsProvider namespaces={i18nNamespaces} locale={locale}>
			<ReactDateRangeClient />
		</TranslationsProvider>
	);
};

export default ReactDateRangePage;
