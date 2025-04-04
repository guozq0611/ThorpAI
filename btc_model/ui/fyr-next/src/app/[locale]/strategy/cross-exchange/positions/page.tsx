'use client';

import React, { useState, useMemo } from 'react';
import PageWrapper from '@/components/layouts/PageWrapper/PageWrapper';
import { useTranslation } from 'react-i18next';
import Card, { CardBody, CardHeader, CardHeaderChild } from '@/components/ui/Card';
import Table, { THead, TBody, Tr, Th, Td } from '@/components/ui/Table';
import Button from '@/components/ui/Button';
import Icon from '@/components/icon/Icon';
import Badge from '@/components/ui/Badge';

const CrossExchangePositionsPage = () => {
	const { t } = useTranslation();
	const [activeTab, setActiveTab] = useState('all');

	const tabs = useMemo(() => [
		{ id: 'all', text: t('全部持仓') },
		{ id: 'long', text: t('多头持仓') },
		{ id: 'short', text: t('空头持仓') },
	], [t]);

	const positions = useMemo(() => [
		{
			id: 1,
			symbol: 'BTC/USDT',
			exchange: 'Binance',
			side: 'long',
			amount: '0.1',
			avgPrice: '50000',
			unrealizedPnl: '100',
			unrealizedPnlPercent: '0.2%',
			leverage: '1',
		},
		{
			id: 2,
			symbol: 'ETH/USDT',
			exchange: 'Huobi',
			side: 'short',
			amount: '1',
			avgPrice: '3000',
			unrealizedPnl: '-50',
			unrealizedPnlPercent: '-0.1%',
			leverage: '1',
		},
	], []);

	return (
		<PageWrapper>
			<div className='flex h-full w-full flex-col gap-4'>
				<div className='flex items-center justify-between'>
					<h1 className='text-2xl font-bold'>{t('跨所套利策略持仓')}</h1>
					<div className='flex gap-2'>
						<Button
							icon='HeroArrowPath'
							onClick={() => {
								// 刷新持仓
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
									<Th className='text-left'>{t('交易对')}</Th>
									<Th className='text-left'>{t('交易所')}</Th>
									<Th className='text-left'>{t('方向')}</Th>
									<Th className='text-right'>{t('持仓数量')}</Th>
									<Th className='text-right'>{t('开仓均价')}</Th>
									<Th className='text-right'>{t('未实现盈亏')}</Th>
									<Th className='text-right'>{t('收益率')}</Th>
									<Th className='text-right'>{t('杠杆')}</Th>
									<Th className='text-center'>{t('操作')}</Th>
								</Tr>
							</THead>
							<TBody>
								{positions.map((position) => (
									<Tr key={position.id}>
										<Td className='text-left'>{position.symbol}</Td>
										<Td className='text-left'>{position.exchange}</Td>
										<Td className='text-left'>
											<Badge
												color={position.side === 'long' ? 'emerald' : 'red'}
												variant='outline'>
												{position.side === 'long' ? t('多头') : t('空头')}
											</Badge>
										</Td>
										<Td className='text-right'>{position.amount}</Td>
										<Td className='text-right'>{position.avgPrice}</Td>
										<Td className='text-right'>
											<span
												className={
													position.unrealizedPnl.startsWith('-')
														? 'text-red-500'
														: 'text-emerald-500'
												}>
												{position.unrealizedPnl}
											</span>
										</Td>
										<Td className='text-right'>
											<span
												className={
													position.unrealizedPnlPercent.startsWith('-')
														? 'text-red-500'
														: 'text-emerald-500'
												}>
												{position.unrealizedPnlPercent}
											</span>
										</Td>
										<Td className='text-right'>{position.leverage}</Td>
										<Td className='text-center'>
											<div className='flex gap-2 justify-center'>
												<Button
													icon='HeroXMark'
													color='red'
													variant='outline'
													onClick={() => {
														// 平仓
													}}
												/>
											</div>
										</Td>
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

export default CrossExchangePositionsPage; 