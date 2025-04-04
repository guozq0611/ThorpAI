'use client';

import React from 'react';
import PageWrapper from '@/components/layouts/PageWrapper/PageWrapper';
import { useTranslation } from 'react-i18next';

const CrossExchangeArbitragePage = () => {
	const { t } = useTranslation();

	return (
		<PageWrapper>
			<div className='flex h-full w-full flex-col gap-4'>
				<div className='flex items-center justify-between'>
					<h1 className='text-2xl font-bold'>{t('跨所套利策略')}</h1>
				</div>
				<div className='grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3'>
					{/* 这里添加跨所套利策略的内容 */}
				</div>
			</div>
		</PageWrapper>
	);
};

export default CrossExchangeArbitragePage; 