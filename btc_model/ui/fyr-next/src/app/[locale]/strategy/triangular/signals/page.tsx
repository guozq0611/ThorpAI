'use client';

import React, { useState, useMemo } from 'react';
import PageWrapper from '@/components/layouts/PageWrapper/PageWrapper';
import { useTranslation } from 'react-i18next';
import Card, { CardBody, CardHeader, CardHeaderChild } from '@/components/ui/Card';
import Table, { THead, TBody, Tr, Th, Td } from '@/components/ui/Table';
import Button from '@/components/ui/Button';
import Icon from '@/components/icon/Icon';
import Badge from '@/components/ui/Badge';

const TriangularSignalsPage = () => {
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
			pair1: 'BTC/USDT',
			pair2: 'ETH/BTC',
			pair3: 'ETH/USDT',
			profit: '1.2%',
			volume: '5 BTC',
			status: 'active',
			timestamp: '2024-04-04 10:30:00',
		},
		{
			id: 2,
			pair1: 'BNB/USDT',
			pair2: 'BTC/BNB',
			pair3: 'BTC/USDT',
			profit: '0.8%',
			volume: '20 BNB',
			status: 'closed',
			timestamp: '2024-04-04 09:15:00',
		},
	], []);

	return (
		<PageWrapper>
			<div className='flex h-full w-full flex-col gap-4'>
				<div className='flex items-center justify-between'>
					<h1 className='text-2xl font-bold'>{t('三角套利交易信号')}</h1>
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
									<Th className='text-left'>{t('交易对1')}</Th>
									<Th className='text-left'>{t('交易对2')}</Th>
									<Th className='text-left'>{t('交易对3')}</Th>
									<Th className='text-right'>{t('预期收益')}</Th>
									<Th className='text-right'>{t('交易量')}</Th>
									<Th className='text-left'>{t('状态')}</Th>
									<Th className='text-right'>{t('时间')}</Th>
									<Th className='text-center'>{t('操作')}</Th>
								</Tr>
							</THead>
							<TBody>
								{signals.map((signal) => (
									<Tr key={signal.id}>
										<Td className='text-left'>{signal.pair1}</Td>
										<Td className='text-left'>{signal.pair2}</Td>
										<Td className='text-left'>{signal.pair3}</Td>
										<Td className='text-right'>{signal.profit}</Td>
										<Td className='text-right'>{signal.volume}</Td>
										<Td className='text-left'>
											<Badge
												color={signal.status === 'active' ? 'emerald' : 'red'}
												variant='outline'>
												{signal.status === 'active' ? t('活跃') : t('已关闭')}
											</Badge>
										</Td>
										<Td className='text-right'>{signal.timestamp}</Td>
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

export default TriangularSignalsPage; 