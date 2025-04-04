'use client';

import React, { useState, useMemo } from 'react';
import PageWrapper from '@/components/layouts/PageWrapper/PageWrapper';
import { useTranslation } from 'react-i18next';
import Card, { CardBody, CardHeader, CardHeaderChild } from '@/components/ui/Card';
import Table, { THead, TBody, Tr, Th, Td } from '@/components/ui/Table';
import Button from '@/components/ui/Button';
import Icon from '@/components/icon/Icon';
import Badge from '@/components/ui/Badge';
import Progress from '@/components/ui/Progress';

const DashboardPage = () => {
	const { t } = useTranslation();
	const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

	// 账户概览数据
	const accountOverview = useMemo(() => ({
		totalBalance: 125000.5,
		availableBalance: 85000.2,
		unrealizedPnL: 2500.3,
		realizedPnL: 1500.8,
		leverage: 3,
		riskLevel: 'medium',
	}), []);

	// 策略数据
	const strategies = useMemo(() => [
		{
			id: 1,
			name: '跨所套利策略',
			description: '利用不同交易所之间的价格差异进行套利',
			status: 'running',
			profit: 1250.5,
			profitPercent: 2.5,
			winRate: 75,
			totalTrades: 120,
			activePositions: 3,
			riskLevel: 'medium',
			lastUpdate: '2024-04-04 10:30:00',
		},
		{
			id: 2,
			name: '三角套利策略',
			description: '通过三个交易对之间的价格差异进行套利',
			status: 'paused',
			profit: 850.2,
			profitPercent: 1.8,
			winRate: 68,
			totalTrades: 95,
			activePositions: 2,
			riskLevel: 'low',
			lastUpdate: '2024-04-04 09:15:00',
		},
		{
			id: 3,
			name: '网格交易策略',
			description: '在价格区间内进行网格交易',
			status: 'stopped',
			profit: -150.3,
			profitPercent: -0.3,
			winRate: 45,
			totalTrades: 200,
			activePositions: 0,
			riskLevel: 'high',
			lastUpdate: '2024-04-04 08:00:00',
		},
	], []);

	// 市场概览数据
	const marketOverview = useMemo(() => ({
		btcPrice: 65000.5,
		btcChange: 2.5,
		ethPrice: 3200.2,
		ethChange: 1.8,
		totalVolume: 1250000000,
		marketTrend: 'up',
	}), []);

	const renderStrategyGrid = () => (
		<div className='grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3'>
			{strategies.map((strategy) => (
				<Card key={strategy.id} className='hover:shadow-lg transition-shadow duration-300'>
					<CardBody>
						<div className='flex flex-col gap-4'>
							<div className='flex items-center justify-between'>
								<h3 className='text-lg font-semibold'>{strategy.name}</h3>
								<Badge
									color={
										strategy.status === 'running'
											? 'emerald'
											: strategy.status === 'paused'
											? 'amber'
											: 'red'
									}
									variant='outline'>
									{strategy.status === 'running'
										? t('运行中')
										: strategy.status === 'paused'
										? t('已暂停')
										: t('已停止')}
								</Badge>
							</div>
							<p className='text-sm text-gray-500'>{strategy.description}</p>
							<div className='flex items-center justify-between'>
								<span className='text-sm text-gray-500'>{t('风险等级')}</span>
								<Badge
									color={
										strategy.riskLevel === 'low'
											? 'emerald'
											: strategy.riskLevel === 'medium'
											? 'amber'
											: 'red'
									}
									variant='outline'>
									{strategy.riskLevel === 'low'
										? t('低风险')
										: strategy.riskLevel === 'medium'
										? t('中风险')
										: t('高风险')}
								</Badge>
							</div>
							<div className='flex items-center justify-between'>
								<span className='text-sm text-gray-500'>{t('总收益')}</span>
								<span
									className={
										strategy.profit >= 0 ? 'text-emerald-500' : 'text-red-500'
									}>
									{strategy.profit >= 0 ? '+' : ''}
									{strategy.profit} ({strategy.profitPercent}%)
								</span>
							</div>
							<div className='flex items-center justify-between'>
								<span className='text-sm text-gray-500'>{t('胜率')}</span>
								<Progress
									value={strategy.winRate}
									color={strategy.winRate >= 60 ? 'emerald' : 'red'}
									className='w-24'
								/>
							</div>
							<div className='flex items-center justify-between'>
								<span className='text-sm text-gray-500'>{t('总交易数')}</span>
								<span>{strategy.totalTrades}</span>
							</div>
							<div className='flex items-center justify-between'>
								<span className='text-sm text-gray-500'>{t('活跃持仓')}</span>
								<span>{strategy.activePositions}</span>
							</div>
							<div className='flex items-center justify-between'>
								<span className='text-sm text-gray-500'>{t('最后更新')}</span>
								<span className='text-sm'>{strategy.lastUpdate}</span>
							</div>
							<div className='flex gap-2 justify-end'>
								<Button
									icon='HeroPlay'
									color='emerald'
									variant='outline'
									onClick={() => {
										// 启动策略
									}}
								/>
								<Button
									icon='HeroPause'
									color='amber'
									variant='outline'
									onClick={() => {
										// 暂停策略
									}}
								/>
								<Button
									icon='HeroStop'
									color='red'
									variant='outline'
									onClick={() => {
										// 停止策略
									}}
								/>
							</div>
						</div>
					</CardBody>
				</Card>
			))}
		</div>
	);

	const renderStrategyList = () => (
		<Table>
			<THead>
				<Tr>
					<Th className='text-left'>{t('策略名称')}</Th>
					<Th className='text-left'>{t('状态')}</Th>
					<Th className='text-left'>{t('风险等级')}</Th>
					<Th className='text-right'>{t('总收益')}</Th>
					<Th className='text-right'>{t('胜率')}</Th>
					<Th className='text-right'>{t('总交易数')}</Th>
					<Th className='text-right'>{t('活跃持仓')}</Th>
					<Th className='text-right'>{t('最后更新')}</Th>
					<Th className='text-center'>{t('操作')}</Th>
				</Tr>
			</THead>
			<TBody>
				{strategies.map((strategy) => (
					<Tr key={strategy.id}>
						<Td className='text-left'>
							<div>
								<div className='font-medium'>{strategy.name}</div>
								<div className='text-sm text-gray-500'>{strategy.description}</div>
							</div>
						</Td>
						<Td className='text-left'>
							<Badge
								color={
									strategy.status === 'running'
										? 'emerald'
										: strategy.status === 'paused'
										? 'amber'
										: 'red'
								}
								variant='outline'>
								{strategy.status === 'running'
									? t('运行中')
									: strategy.status === 'paused'
									? t('已暂停')
									: t('已停止')}
							</Badge>
						</Td>
						<Td className='text-left'>
							<Badge
								color={
									strategy.riskLevel === 'low'
										? 'emerald'
										: strategy.riskLevel === 'medium'
										? 'amber'
										: 'red'
								}
								variant='outline'>
								{strategy.riskLevel === 'low'
									? t('低风险')
									: strategy.riskLevel === 'medium'
									? t('中风险')
									: t('高风险')}
							</Badge>
						</Td>
						<Td className='text-right'>
							<span
								className={
									strategy.profit >= 0 ? 'text-emerald-500' : 'text-red-500'
								}>
								{strategy.profit >= 0 ? '+' : ''}
								{strategy.profit} ({strategy.profitPercent}%)
							</span>
						</Td>
						<Td className='text-right'>
							<Progress
								value={strategy.winRate}
								color={strategy.winRate >= 60 ? 'emerald' : 'red'}
								className='w-24'
							/>
						</Td>
						<Td className='text-right'>{strategy.totalTrades}</Td>
						<Td className='text-right'>{strategy.activePositions}</Td>
						<Td className='text-right'>{strategy.lastUpdate}</Td>
						<Td className='text-center'>
							<div className='flex gap-2 justify-center'>
								<Button
									icon='HeroPlay'
									color='emerald'
									variant='outline'
									onClick={() => {
										// 启动策略
									}}
								/>
								<Button
									icon='HeroPause'
									color='amber'
									variant='outline'
									onClick={() => {
										// 暂停策略
									}}
								/>
								<Button
									icon='HeroStop'
									color='red'
									variant='outline'
									onClick={() => {
										// 停止策略
									}}
								/>
							</div>
						</Td>
					</Tr>
				))}
			</TBody>
		</Table>
	);

	return (
		<PageWrapper>
			<div className='flex h-full w-full flex-col gap-4'>
				{/* 账户概览 */}
				<div className='grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4'>
					<Card>
						<CardBody>
							<div className='flex flex-col gap-2'>
								<div className='text-sm text-gray-500'>{t('总资产')}</div>
								<div className='text-2xl font-bold'>
									${accountOverview.totalBalance.toLocaleString()}
								</div>
								<div className='flex items-center gap-2'>
									<Badge color='emerald' variant='outline'>
										{t('杠杆')}: {accountOverview.leverage}x
									</Badge>
									<Badge
										color={
											accountOverview.riskLevel === 'low'
												? 'emerald'
												: accountOverview.riskLevel === 'medium'
												? 'amber'
												: 'red'
										}
										variant='outline'>
										{accountOverview.riskLevel === 'low'
											? t('低风险')
											: accountOverview.riskLevel === 'medium'
											? t('中风险')
											: t('高风险')}
									</Badge>
								</div>
							</div>
						</CardBody>
					</Card>
					<Card>
						<CardBody>
							<div className='flex flex-col gap-2'>
								<div className='text-sm text-gray-500'>{t('可用余额')}</div>
								<div className='text-2xl font-bold'>
									${accountOverview.availableBalance.toLocaleString()}
								</div>
							</div>
						</CardBody>
					</Card>
					<Card>
						<CardBody>
							<div className='flex flex-col gap-2'>
								<div className='text-sm text-gray-500'>{t('未实现盈亏')}</div>
								<div
									className={`text-2xl font-bold ${
										accountOverview.unrealizedPnL >= 0
											? 'text-emerald-500'
											: 'text-red-500'
									}`}>
									{accountOverview.unrealizedPnL >= 0 ? '+' : ''}
									${accountOverview.unrealizedPnL.toLocaleString()}
								</div>
							</div>
						</CardBody>
					</Card>
					<Card>
						<CardBody>
							<div className='flex flex-col gap-2'>
								<div className='text-sm text-gray-500'>{t('已实现盈亏')}</div>
								<div
									className={`text-2xl font-bold ${
										accountOverview.realizedPnL >= 0
											? 'text-emerald-500'
											: 'text-red-500'
									}`}>
									{accountOverview.realizedPnL >= 0 ? '+' : ''}
									${accountOverview.realizedPnL.toLocaleString()}
								</div>
							</div>
						</CardBody>
					</Card>
				</div>

				{/* 市场概览 */}
				<Card>
					<CardHeader>
						<CardHeaderChild>
							<div className='text-lg font-semibold'>{t('市场概览')}</div>
						</CardHeaderChild>
					</CardHeader>
					<CardBody>
						<div className='grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4'>
							<div className='flex flex-col gap-2'>
								<div className='text-sm text-gray-500'>{t('BTC价格')}</div>
								<div className='text-xl font-bold'>
									${marketOverview.btcPrice.toLocaleString()}
								</div>
								<div
									className={`text-sm ${
										marketOverview.btcChange >= 0
											? 'text-emerald-500'
											: 'text-red-500'
									}`}>
									{marketOverview.btcChange >= 0 ? '+' : ''}
									{marketOverview.btcChange}%
								</div>
							</div>
							<div className='flex flex-col gap-2'>
								<div className='text-sm text-gray-500'>{t('ETH价格')}</div>
								<div className='text-xl font-bold'>
									${marketOverview.ethPrice.toLocaleString()}
								</div>
								<div
									className={`text-sm ${
										marketOverview.ethChange >= 0
											? 'text-emerald-500'
											: 'text-red-500'
									}`}>
									{marketOverview.ethChange >= 0 ? '+' : ''}
									{marketOverview.ethChange}%
								</div>
							</div>
							<div className='flex flex-col gap-2'>
								<div className='text-sm text-gray-500'>{t('24小时交易量')}</div>
								<div className='text-xl font-bold'>
									${(marketOverview.totalVolume / 1000000).toFixed(2)}M
								</div>
							</div>
							<div className='flex flex-col gap-2'>
								<div className='text-sm text-gray-500'>{t('市场趋势')}</div>
								<div className='text-xl font-bold'>
									<Badge
										color={marketOverview.marketTrend === 'up' ? 'emerald' : 'red'}
										variant='outline'>
										{marketOverview.marketTrend === 'up'
											? t('上涨')
											: t('下跌')}
									</Badge>
								</div>
							</div>
						</div>
					</CardBody>
				</Card>

				{/* 策略概览 */}
				<Card>
					<CardHeader>
						<CardHeaderChild>
							<div className='text-lg font-semibold'>{t('策略概览')}</div>
						</CardHeaderChild>
						<CardHeaderChild>
							<div className='flex gap-2'>
								<Button
									icon={viewMode === 'grid' ? 'HeroBars3' : 'HeroSquares2X2'}
									onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}>
									{viewMode === 'grid' ? t('列表视图') : t('卡片视图')}
								</Button>
								<Button
									icon='HeroArrowPath'
									onClick={() => {
										// 刷新策略数据
									}}>
									{t('刷新')}
								</Button>
							</div>
						</CardHeaderChild>
					</CardHeader>
					<CardBody>
						{viewMode === 'grid' ? renderStrategyGrid() : renderStrategyList()}
					</CardBody>
				</Card>
			</div>
		</PageWrapper>
	);
};

export default DashboardPage; 