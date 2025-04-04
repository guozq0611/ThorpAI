'use client';

import React, { useState, useMemo } from 'react';
import PageWrapper from '@/components/layouts/PageWrapper/PageWrapper';
import { useTranslation } from 'react-i18next';
import Card, { CardBody, CardHeader, CardHeaderChild } from '@/components/ui/Card';
import Table, { THead, TBody, Tr, Th, Td } from '@/components/ui/Table';
import Button from '@/components/ui/Button';
import Icon from '@/components/icon/Icon';
import Badge from '@/components/ui/Badge';

const CrossExchangeSignalsPage = () => {
	const { t } = useTranslation();
	const [activeTab, setActiveTab] = useState('all');

	const tabs = useMemo(() => [
		{ id: 'all', text: t('全部信号') },
		{ id: 'active', text: t('活跃信号') },
		{ id: 'closed', text: t('已关闭信号') },
	], [t]);

	const signals = useMemo(() => [
		{
			id: 1,
			pair: 'BTC/USDT',
			exchange1: 'Binance',
			exchange2: 'Huobi',
			priceDiff: '2.5%',
			volume: '10 BTC',
			status: 'active',
			timestamp: '2024-04-04 10:30:00',
		},
		{
			id: 2,
			pair: 'ETH/USDT',
			exchange1: 'OKX',
			exchange2: 'Binance',
			priceDiff: '1.8%',
			volume: '50 ETH',
			status: 'closed',
			timestamp: '2024-04-04 09:15:00',
		},
	], []);

	return (
		<PageWrapper>
			<div className='flex h-full w-full flex-col gap-4'>
				<div className='flex items-center justify-between'>
					<h1 className='text-2xl font-bold'>{t('cross exchange arbitrage signals')}</h1>
					<div className='flex gap-2'>
						<Button
							icon='HeroPlus'
							onClick={() => {
								// 添加新信号
							}}>
							{t('添加信号')}
						</Button>
						<Button
							icon='HeroArrowPath'
							onClick={() => {
								// 刷新信号
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
									<Th className='text-left'>{t('symbol')}</Th>
									<Th className='text-left'>{t('exchage_1')}</Th>
									<Th className='text-left'>{t('exchage_2')}</Th>
									<Th className='text-right'>{t('spread')}</Th>
									<Th className='text-right'>{t('volume')}</Th>
									<Th className='text-left'>{t('status')}</Th>
									<Th className='text-left'>{t('updatetime')}</Th>
									<Th className='text-center'>{t('operation')}</Th>
								</Tr>
							</THead>
							<TBody>
								{signals.map((signal) => (
									<Tr key={signal.id}>
										<Td className='text-left'>{signal.pair}</Td>
										<Td className='text-left'>{signal.exchange1}</Td>
										<Td className='text-left'>{signal.exchange2}</Td>
										<Td className='text-right'>{signal.priceDiff}</Td>
										<Td className='text-right'>{signal.volume}</Td>
										<Td className='text-left'>
											<Badge
												color={signal.status === 'active' ? 'emerald' : 'red'}
												variant='outline'>
												{signal.status === 'active' ? t('活跃') : t('已关闭')}
											</Badge>
										</Td>
										<Td className='text-left'>{signal.timestamp}</Td>
										<Td className='text-center'>
											<div className='flex gap-2 justify-center'>
												<Button
													icon='HeroEye'
													color='blue'
													variant='outline'
													onClick={() => {
														// 查看详情
													}}
												/>
												<Button
													icon='HeroPencilSquare'
													color='amber'
													variant='outline'
													onClick={() => {
														// 编辑
													}}
												/>
												<Button
													icon='HeroTrash'
													color='red'
													variant='outline'
													onClick={() => {
														// 删除
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

export default CrossExchangeSignalsPage; 