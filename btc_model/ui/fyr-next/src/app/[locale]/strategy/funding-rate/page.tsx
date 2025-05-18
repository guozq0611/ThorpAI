'use client';

import React, { useState } from 'react';
import Card, { CardBody, CardHeader, CardTitle } from '../../../../components/ui/Card';
import PageWrapper from '../../../../components/layouts/PageWrapper/PageWrapper';
import Button from '../../../../components/ui/Button';
import Icon from '../../../../components/icon/Icon';
import Chart from '../../../../components/Chart';
import Badge from '../../../../components/ui/Badge';
import Progress from '../../../../components/ui/Progress';
import Link from 'next/link';

const FundingRateStrategyPage = () => {
	// 模拟数据
	const strategyStats = {
		status: 'active',
		activePositions: 3,
		totalPositions: 12,
		totalPnL: '+4.28%',
		currentOpportunities: 5,
		averageFundingRate: '0.0062',
		totalWhitelistedPairs: 8,
	};

	// 历史收益率图表选项
	const pnlChartOptions = {
		series: [
			{
				name: '收益率',
				data: [1.2, 1.8, 2.5, 3.1, 2.9, 3.5, 4.28],
			},
		],
		options: {
			chart: {
				height: 350,
				type: 'line' as const,
				toolbar: {
					show: false,
				},
			},
			colors: ['#0ea5e9'],
			dataLabels: {
				enabled: false,
			},
			stroke: {
				curve: 'smooth' as const,
				width: 3,
			},
			xaxis: {
				categories: ['6/1', '6/8', '6/15', '6/22', '6/29', '7/6', '7/13'],
				labels: {
					style: {
						colors: '#64748b',
					},
				},
			},
			yaxis: {
				labels: {
					formatter: function (value: number) {
						return value.toFixed(2) + '%';
					},
					style: {
						colors: '#64748b',
					},
				},
			},
			tooltip: {
				y: {
					formatter: function (value: number) {
						return value.toFixed(2) + '%';
					},
				},
			},
			grid: {
				borderColor: '#e2e8f0',
			},
			markers: {
				size: 5,
			},
		},
	};

	// 资金费率趋势图表选项
	const fundingRateChartOptions = {
		series: [
			{
				name: '平均资金费率',
				data: [0.0058, 0.0064, 0.0072, 0.0068, 0.0060, 0.0057, 0.0062],
			},
		],
		options: {
			chart: {
				height: 350,
				type: 'area' as const,
				toolbar: {
					show: false,
				},
			},
			colors: ['#8b5cf6'],
			dataLabels: {
				enabled: false,
			},
			stroke: {
				curve: 'smooth' as const,
				width: 2,
			},
			xaxis: {
				categories: ['6/1', '6/8', '6/15', '6/22', '6/29', '7/6', '7/13'],
				labels: {
					style: {
						colors: '#64748b',
					},
				},
			},
			yaxis: {
				labels: {
					formatter: function (value: number) {
						return (value * 100).toFixed(2) + '%';
					},
					style: {
						colors: '#64748b',
					},
				},
			},
			tooltip: {
				y: {
					formatter: function (value: number) {
						return (value * 100).toFixed(2) + '%';
					},
				},
			},
			fill: {
				type: 'gradient',
				gradient: {
					shadeIntensity: 1,
					opacityFrom: 0.7,
					opacityTo: 0.2,
					stops: [0, 100],
				},
			},
			grid: {
				borderColor: '#e2e8f0',
			},
		},
	};

	// 最近交易队列，显示最近5笔交易
	const recentTrades = [
		{
			id: '1',
			pair: 'BTC-USDT',
			type: 'open',
			pnl: null,
			time: '2023-07-13 10:45:21',
		},
		{
			id: '2',
			pair: 'SOL-USDT',
			type: 'close',
			pnl: '+2.85%',
			time: '2023-07-12 15:32:18',
		},
		{
			id: '3',
			pair: 'ETH-USDT',
			type: 'open',
			pnl: null,
			time: '2023-07-12 09:22:45',
		},
		{
			id: '4',
			pair: 'XRP-USDT',
			type: 'close',
			pnl: '+1.32%',
			time: '2023-07-11 16:58:09',
		},
		{
			id: '5',
			pair: 'BNB-USDT',
			type: 'close',
			pnl: '-0.75%',
			time: '2023-07-10 14:10:33',
		},
	];

	return (
		<PageWrapper>
			<div className="flex justify-between items-center mb-5">
				<h1 className="text-2xl font-bold">资金费率套利策略</h1>
				<div className="flex gap-2">
					<Link href="/strategy/funding-rate/arbitrage">
						<Button 
							variant="solid" 
							color="blue" 
							icon="HeroTable">
							套利列表
						</Button>
					</Link>
					<Link href="/strategy/funding-rate/whitelist">
						<Button 
							variant="outline" 
							color="blue" 
							icon="HeroListBullet">
							管理白名单
						</Button>
					</Link>
				</div>
			</div>
			
			<div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-5">
				{/* 策略状态卡片 */}
				<Card className="col-span-1">
					<CardBody>
						<div className="flex justify-between items-center">
							<div>
								<div className="text-gray-500 mb-1">策略状态</div>
								<div className="text-2xl font-bold flex items-center gap-2">
									<Badge
										color={strategyStats.status === 'active' ? 'emerald' : 'red'}
										className="text-sm">
										{strategyStats.status === 'active' ? '运行中' : '已停止'}
									</Badge>
								</div>
							</div>
							<div className="bg-info-100 p-3 rounded-full">
								<Icon
									icon="HeroRocketLaunch"
									className="text-blue-500 h-6 w-6"
								/>
							</div>
						</div>
					</CardBody>
				</Card>

				{/* 活跃仓位卡片 */}
				<Card className="col-span-1">
					<CardBody>
						<div className="flex justify-between items-center">
							<div>
								<div className="text-gray-500 mb-1">活跃仓位</div>
								<div className="text-2xl font-bold">
									{strategyStats.activePositions} / {strategyStats.totalPositions}
								</div>
							</div>
							<div className="bg-success-100 p-3 rounded-full">
								<Icon
									icon="HeroChartBar"
									className="text-emerald-500 h-6 w-6"
								/>
							</div>
						</div>
					</CardBody>
				</Card>

				{/* 总收益率卡片 */}
				<Card className="col-span-1">
					<CardBody>
						<div className="flex justify-between items-center">
							<div>
								<div className="text-gray-500 mb-1">总收益率</div>
								<div className="text-2xl font-bold text-emerald-500">
									{strategyStats.totalPnL}
								</div>
							</div>
							<div className="bg-warning-100 p-3 rounded-full">
								<Icon
									icon="HeroCurrencyDollar"
									className="text-amber-500 h-6 w-6"
								/>
							</div>
						</div>
					</CardBody>
				</Card>

				{/* 当前机会卡片 */}
				<Card className="col-span-1">
					<CardBody>
						<div className="flex justify-between items-center">
							<div>
								<div className="text-gray-500 mb-1">当前机会</div>
								<div className="text-2xl font-bold">
									{strategyStats.currentOpportunities}
								</div>
							</div>
							<div className="bg-danger-100 p-3 rounded-full">
								<Icon
									icon="HeroLightBulb"
									className="text-red-500 h-6 w-6"
								/>
							</div>
						</div>
					</CardBody>
				</Card>
			</div>

			<div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-5">
				{/* 收益率走势图表 */}
				<Card className="col-span-1 lg:col-span-2">
					<CardHeader>
						<CardTitle>收益率走势</CardTitle>
					</CardHeader>
					<CardBody>
						<Chart
							series={pnlChartOptions.series}
							options={pnlChartOptions.options}
							type="line"
							height={350}
						/>
					</CardBody>
				</Card>

				{/* 最近交易 */}
				<Card className="col-span-1">
					<CardHeader>
						<CardTitle>最近交易</CardTitle>
					</CardHeader>
					<CardBody>
						<div className="flex flex-col gap-3">
							{recentTrades.map((trade) => (
								<div
									key={trade.id}
									className="flex justify-between items-center p-3 border-b border-gray-100 last:border-0">
									<div>
										<div className="font-bold">{trade.pair}</div>
										<div className="text-xs text-gray-500">{trade.time}</div>
									</div>
									<div className="flex items-center gap-2">
										<Badge
											color={trade.type === 'open' ? 'blue' : 'amber'}
											className="text-xs">
											{trade.type === 'open' ? '开仓' : '平仓'}
										</Badge>
										{trade.pnl && (
											<span
												className={`font-bold ${
													trade.pnl.startsWith('+')
														? 'text-emerald-500'
														: 'text-red-500'
												}`}>
												{trade.pnl}
											</span>
										)}
									</div>
								</div>
							))}
							<Button
								variant="outline"
								color="blue"
								className="w-full mt-2"
								icon="HeroArrowRight">
								查看全部交易
							</Button>
						</div>
					</CardBody>
				</Card>
			</div>

			<div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
				{/* 资金费率趋势图表 */}
				<Card className="col-span-1 lg:col-span-2">
					<CardHeader>
						<CardTitle>资金费率趋势</CardTitle>
					</CardHeader>
					<CardBody>
						<Chart
							series={fundingRateChartOptions.series}
							options={fundingRateChartOptions.options}
							type="area"
							height={350}
						/>
					</CardBody>
				</Card>

				{/* 白名单概览 */}
				<Card className="col-span-1">
					<CardHeader>
						<CardTitle>白名单概览</CardTitle>
					</CardHeader>
					<CardBody>
						<div className="flex flex-col gap-4">
							<div className="flex justify-between items-center">
								<div className="text-gray-600">白名单交易对</div>
								<div className="font-bold">{strategyStats.totalWhitelistedPairs}</div>
							</div>
							<div className="flex justify-between items-center">
								<div className="text-gray-600">平均资金费率</div>
								<div className="font-bold">
									{parseFloat(strategyStats.averageFundingRate) * 100}%
								</div>
							</div>
							<div className="flex flex-col gap-2">
								<div className="flex justify-between text-sm">
									<span>交易对利用率</span>
									<span className="font-semibold">
										{strategyStats.activePositions} / {strategyStats.totalWhitelistedPairs}
									</span>
								</div>
								<Progress
									value={(strategyStats.activePositions / strategyStats.totalWhitelistedPairs) * 100}
									color="blue"
									className="h-2"
								/>
							</div>
							<Button
								variant="solid"
								color="blue"
								className="w-full mt-2"
								icon="HeroListBullet">
								管理白名单
							</Button>
						</div>
					</CardBody>
				</Card>
			</div>
		</PageWrapper>
	);
};

export default FundingRateStrategyPage; 