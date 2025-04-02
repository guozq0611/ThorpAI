import React from 'react';
import ProfileClient from '@/app/[locale]/profile/client';
import TranslationsProvider from '@/components/TranslationsProvider';

const i18nNamespaces = ['translation'];

const Profile = ({ params: { locale } }: { params: { locale: string } }) => {
	return (
		<TranslationsProvider namespaces={i18nNamespaces} locale={locale}>
			<ProfileClient />
		</TranslationsProvider>
	);
};

export default Profile;
