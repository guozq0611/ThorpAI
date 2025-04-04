'use client';

import React, { useState, useMemo } from 'react';
import PageWrapper from '@/components/layouts/PageWrapper/PageWrapper';
import { useTranslation } from 'react-i18next';
import Card, { CardBody, CardHeader, CardHeaderChild } from '@/components/ui/Card';
import Table, { THead, TBody, Tr, Th, Td } from '@/components/ui/Table';
import Button from '@/components/ui/Button';
import Icon from '@/components/icon/Icon';
import Badge from '@/components/ui/Badge';

const TriangularTradesPage = () => {
	const { t } = useTranslation();
	const [activeTab, setActiveTab] = useState('all');

	const tabs = useMemo(() => [
		{ id: 'all', text: t('全部成交') },
		{ id: 'today', text: t('今日成交') },
		{ id: 'yesterday', text: t('昨日成交') },
	], [t]);

	const trades = useMemo(() => [
		{
			id: 1,
			pair1: 'BTC/USDT',
			pair2: 'ETH/BTC',
			pair3: 'ETH/USDT',
			exchange: 'Binance',
			side: 'buy',
			price: '50000',
			amount: '0.1',
			fee: '0.0001',
			timestamp: '2024-04-04 10:30:00',
		},
		{
			id: 2,
			pair1: 'BNB/USDT',
			pair2: 'BTC/BNB',
			pair3: 'BTC/USDT',
			exchange: 'Binance',
			side: 'sell',
			price: '300',
			amount: '10',
			fee: '0.0001',
			timestamp: '2024-04-04 09:15:00',
		},
	], []);

	return (
		<PageWrapper>
			<div className='flex h-full w-full flex-col gap-4'>
				<div className='flex items-center justify-between'>
					<h1 className='text-2xl font-bold'>{t('三角套利成交订单')}</h1>
					<div className='flex gap-2'>
						<Button
							icon='HeroArrowPath'
							onClick={() => {
								// 刷新成交
							}}>
							{t('刷新')}
						</Button>
					</div>
				</div>

				<Card>
					<CardHeader>
						<CardHeaderChild>
							<div className='flex gap-2'>
								{tabs.map((tab) => (
									<Button
										key={tab.id}
										variant={activeTab === tab.id ? 'solid' : 'outline'}
										onClick={() => setActiveTab(tab.id)}>
										{tab.text}
									</Button>
								))}
							</div>
						</CardHeaderChild>
					</CardHeader>
					<CardBody>
						<Table>
							<THead>
								<Tr>
									<Th className='text-left'>{t('交易对1')}</Th>
									<Th className='text-left'>{t('交易对2')}</Th>
									<Th className='text-left'>{t('交易对3')}</Th>
									<Th className='text-left'>{t('交易所')}</Th>
									<Th className='text-left'>{t('方向')}</Th>
									<Th className='text-right'>{t('价格')}</Th>
									<Th className='text-right'>{t('数量')}</Th>
									<Th className='text-right'>{t('手续费')}</Th>
									<Th className='text-right'>{t('时间')}</Th>
								</Tr>
							</THead>
							<TBody>
								{trades.map((trade) => (
									<Tr key={trade.id}>
										<Td className='text-left'>{trade.pair1}</Td>
										<Td className='text-left'>{trade.pair2}</Td>
										<Td className='text-left'>{trade.pair3}</Td>
										<Td className='text-left'>{trade.exchange}</Td>
										<Td className='text-left'>
											<Badge
												color={trade.side === 'buy' ? 'emerald' : 'red'}
												variant='outline'>
												{trade.side === 'buy' ? t('买入') : t('卖出')}
											</Badge>
										</Td>
										<Td className='text-right'>{trade.price}</Td>
										<Td className='text-right'>{trade.amount}</Td>
										<Td className='text-right'>{trade.fee}</Td>
										<Td className='text-right'>{trade.timestamp}</Td>
									</Tr>
								))}
							</TBody>
						</Table>
					</CardBody>
				</Card>
			</div>
		</PageWrapper>
	);
};

export default TriangularTradesPage; 