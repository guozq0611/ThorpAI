'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Card, { CardBody, CardHeader, CardTitle, CardHeaderChild } from '../../../../../components/ui/Card';
import PageWrapper from '../../../../../components/layouts/PageWrapper/PageWrapper';
import Button from '../../../../../components/ui/Button';
import Icon from '../../../../../components/icon/Icon';
import Table, { THead, TBody, Tr, Th, Td } from '../../../../../components/ui/Table';
import Badge from '../../../../../components/ui/Badge';
import Input from '../../../../../components/form/Input';
import Select from '../../../../../components/form/Select';
import Dropdown, { DropdownItem, DropdownMenu, DropdownToggle } from '../../../../../components/ui/Dropdown';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import Tooltip from '../../../../../components/ui/Tooltip';

// 资金费率套利数据接口
interface ArbitrageItem {
	id: number;
	symbol: string;
	pair: string;
	combination: string;
	exchange: string;
	funding_rate: number;
	daily_return: number;
	three_day_cumulative: number;
	three_day_return: number;
	annual_rate: number;
	annual_return: number;
	status: string;
	score: number;
	last_update: string;
}

// 排序相关类型
type SortColumn = 'annual_return' | 'daily_return' | 'funding_rate' | 'score';
type SortDirection = 'asc' | 'desc';

const FundingRateArbitragePage = () => {
	const pathname = usePathname();
	
	// 模拟资金费率套利数据
	const [arbitrageData, setArbitrageData] = useState<ArbitrageItem[]>([
		{
			id: 1,
			symbol: 'BTC',
			pair: 'BTC/USDT',
			combination: '永续合约/现货',
			exchange: 'Binance',
			funding_rate: 0.0012, // 单个周期资金费率
			daily_return: 0.0036, // 日收益
			three_day_cumulative: 0.0108, // 三日累计
			three_day_return: 0.0108, // 三日收益
			annual_rate: 1.314, // 年化费率
			annual_return: 1.314, // 年收益
			status: 'active',
			score: 92,
			last_update: '2023-07-13T10:45:21',
		},
		{
			id: 2,
			symbol: 'ETH',
			pair: 'ETH/USDT',
			combination: '永续合约/现货',
			exchange: 'OKX',
			funding_rate: 0.0010,
			daily_return: 0.0030,
			three_day_cumulative: 0.0090,
			three_day_return: 0.0090,
			annual_rate: 1.095,
			annual_return: 1.095,
			status: 'active',
			score: 85,
			last_update: '2023-07-12T15:32:18',
		},
		{
			id: 3,
			symbol: 'SOL',
			pair: 'SOL/USDT',
			combination: '永续合约/现货',
			exchange: 'Binance',
			funding_rate: 0.0015,
			daily_return: 0.0045,
			three_day_cumulative: 0.0135,
			three_day_return: 0.0135,
			annual_rate: 1.6425,
			annual_return: 1.6425,
			status: 'active',
			score: 94,
			last_update: '2023-07-12T09:22:45',
		},
		{
			id: 4,
			symbol: 'XRP',
			pair: 'XRP/USDT',
			combination: '永续合约/现货',
			exchange: 'Bitget',
			funding_rate: 0.0008,
			daily_return: 0.0024,
			three_day_cumulative: 0.0072,
			three_day_return: 0.0072,
			annual_rate: 0.876,
			annual_return: 0.876,
			status: 'active',
			score: 78,
			last_update: '2023-07-11T16:58:09',
		},
		{
			id: 5,
			symbol: 'BNB',
			pair: 'BNB/USDT',
			combination: '永续合约/现货',
			exchange: 'OKX',
			funding_rate: 0.0009,
			daily_return: 0.0027,
			three_day_cumulative: 0.0081,
			three_day_return: 0.0081,
			annual_rate: 0.9855,
			annual_return: 0.9855,
			status: 'active',
			score: 82,
			last_update: '2023-07-10T14:10:33',
		},
	]);

	// 筛选条件状态
	const [filters, setFilters] = useState({
		positionSize: 1000,
		exchange: 'all',
		direction: 'all',
		search: '',
	});

	// 排序状态
	const [sortConfig, setSortConfig] = useState<{
		key: SortColumn;
		direction: SortDirection;
	}>({
		key: 'annual_return',
		direction: 'desc',
	});

	// 选中行状态
	const [selectedRow, setSelectedRow] = useState<number | null>(null);

	// 是否正在加载
	const [isLoading, setIsLoading] = useState<boolean>(false);
	
	// 当前时间，用于计算时间差
	const [currentTime, setCurrentTime] = useState(new Date());

	// 可选择的交易所
	const exchangeOptions = [
		{ value: 'all', text: '全部' },
		{ value: 'Binance', text: 'Binance' },
		{ value: 'OKX', text: 'OKX' },
		{ value: 'Bybit', text: 'Bybit' },
		{ value: 'Bitget', text: 'Bitget' },
	];

	// 可选择的方向
	const directionOptions = [
		{ value: 'all', text: '全部' },
		{ value: 'long', text: '做多' },
		{ value: 'short', text: '做空' },
	];

	// 可选择的头寸大小
	const positionSizeOptions = [
		{ value: 100, text: '$100' },
		{ value: 500, text: '$500' },
		{ value: 1000, text: '$1000' },
		{ value: 5000, text: '$5000' },
		{ value: 10000, text: '$10000' },
	];

	// 定期更新当前时间
	useEffect(() => {
		const timer = setInterval(() => {
			setCurrentTime(new Date());
		}, 30000); // 每30秒更新一次
		
		return () => clearInterval(timer);
	}, []);

	// 获取时间差
	const getTimeDifference = (timestamp: string): { text: string; isStale: boolean } => {
		const date = new Date(timestamp);
		const now = currentTime;
		const diffMs = now.getTime() - date.getTime();
		const diffSec = Math.floor(diffMs / 1000);
		const diffMin = Math.floor(diffSec / 60);
		const diffHour = Math.floor(diffMin / 60);
		const diffDay = Math.floor(diffHour / 24);
		
		// 判断数据是否过期（超过5分钟视为过期）
		const isStale = diffMs > 5 * 60 * 1000;
		
		if (diffSec < 60) {
			return { text: `${diffSec}秒前`, isStale };
		} else if (diffMin < 60) {
			return { text: `${diffMin}分钟前`, isStale };
		} else if (diffHour < 24) {
			return { text: `${diffHour}小时前`, isStale };
		} else {
			return { text: `${diffDay}天前`, isStale: true };
		}
	};

	// 格式化时间戳
	const formatTimestamp = (timestamp: string): string => {
		const date = new Date(timestamp);
		return date.toLocaleString('zh-CN', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit'
		});
	};

	// 排序处理函数
	const handleSort = (key: SortColumn) => {
		let direction: SortDirection = 'desc';
		if (sortConfig.key === key && sortConfig.direction === 'desc') {
			direction = 'asc';
		}
		setSortConfig({ key, direction });
	};

	// 处理行点击
	const handleRowClick = (id: number) => {
		setSelectedRow(selectedRow === id ? null : id);
	};

	// 获取状态徽章
	const getStatusBadge = (status: string) => {
		switch (status.toLowerCase()) {
			case 'active':
				return <Badge color="emerald">活跃</Badge>;
			case 'inactive':
				return <Badge color="amber">未启用</Badge>;
			default:
				return <Badge color="zinc">未知</Badge>;
		}
	};

	// 获取排序图标
	const renderSortIcon = (column: string) => {
		if (sortConfig.key === column) {
			return (
				<Icon 
					icon={sortConfig.direction === 'asc' ? 'HeroArrowUp' : 'HeroArrowDown'} 
					className="h-4 w-4 ml-1 text-blue-500" 
				/>
			);
		}
		return <Icon icon="HeroArrowsUpDown" className="h-4 w-4 ml-1 text-gray-400" />;
	};

	// 刷新数据
	const refreshData = () => {
		setIsLoading(true);
		// 模拟API请求延迟
		setTimeout(() => {
			// 这里应该是真实的API调用
			setIsLoading(false);
		}, 1000);
	};

	// 执行交易
	const handleTrade = (id: number, e: React.MouseEvent) => {
		e.stopPropagation();
		console.log('执行交易:', id);
		// 这里添加交易执行逻辑
	};

	// 查看详情
	const handleViewDetails = (id: number, e: React.MouseEvent) => {
		e.stopPropagation();
		console.log('查看详情:', id);
		// 实现查看详情逻辑
	};

	// 模拟添加到白名单
	const handleAddToWhitelist = (id: number, e: React.MouseEvent) => {
		e.stopPropagation();
		console.log('添加到白名单:', id);
		// 实现添加到白名单逻辑
	};

	// 筛选和排序数据
	const filteredAndSortedData = React.useMemo(() => {
		let filtered = [...arbitrageData];
		
		// 应用搜索筛选
		if (filters.search.trim() !== '') {
			const searchLower = filters.search.toLowerCase();
			filtered = filtered.filter(item => 
				item.symbol.toLowerCase().includes(searchLower) || 
				item.pair.toLowerCase().includes(searchLower) ||
				item.exchange.toLowerCase().includes(searchLower)
			);
		}
		
		// 应用交易所筛选
		if (filters.exchange !== 'all') {
			filtered = filtered.filter(item => item.exchange === filters.exchange);
		}
		
		// 应用方向筛选
		if (filters.direction !== 'all') {
			// 这里需要根据实际数据结构调整筛选逻辑
			filtered = filtered.filter(item => {
				if (filters.direction === 'long') {
					return item.funding_rate > 0;
				} else {
					return item.funding_rate < 0;
				}
			});
		}
		
		// 应用排序
		if (sortConfig.key) {
			filtered.sort((a, b) => {
				if (a[sortConfig.key] < b[sortConfig.key]) {
					return sortConfig.direction === 'asc' ? -1 : 1;
				}
				if (a[sortConfig.key] > b[sortConfig.key]) {
					return sortConfig.direction === 'asc' ? 1 : -1;
				}
				return 0;
			});
		}
		
		return filtered;
	}, [arbitrageData, filters, sortConfig]);

	return (
		<PageWrapper>
			<div className="flex flex-col gap-4">
				<Card>
					<CardHeader>
						<CardHeaderChild>
							<CardTitle className="text-2xl font-bold">资金费率套利</CardTitle>
						</CardHeaderChild>
						<CardHeaderChild>
							<div className="flex gap-2">
								<Input
									type="text"
									placeholder="搜索币种或交易所..."
									value={filters.search}
									onChange={(e) => setFilters({...filters, search: e.target.value})}
									className="w-64"
								/>
								<Button 
									variant="solid" 
									color="blue" 
									icon="HeroArrowPathRoundedSquare"
									onClick={refreshData}
									isLoading={isLoading}>
									刷新数据
								</Button>
								<Link href={`${pathname}/../whitelist`}>
									<Button 
										variant="outline" 
										color="blue" 
										icon="HeroListBullet">
										管理白名单
									</Button>
								</Link>
							</div>
						</CardHeaderChild>
					</CardHeader>
					
					{/* 筛选器 */}
					<CardBody>
						<div className="flex flex-wrap gap-4 mb-4">
							<div className="flex items-center gap-2">
								<span className="text-sm font-medium text-gray-700">头寸大小:</span>
								<Select
									className="min-w-[120px]"
									value={filters.positionSize}
									onChange={(e) => setFilters({...filters, positionSize: Number(e.target.value)})}
									options={positionSizeOptions}
								/>
							</div>
							<div className="flex items-center gap-2">
								<span className="text-sm font-medium text-gray-700">交易所:</span>
								<Select
									className="min-w-[120px]"
									value={filters.exchange}
									onChange={(e) => setFilters({...filters, exchange: e.target.value})}
									options={exchangeOptions}
								/>
							</div>
							<div className="flex items-center gap-2">
								<span className="text-sm font-medium text-gray-700">方向:</span>
								<Select
									className="min-w-[120px]"
									value={filters.direction}
									onChange={(e) => setFilters({...filters, direction: e.target.value})}
									options={directionOptions}
								/>
							</div>
						</div>
						
						{/* 资金费率套利表格 */}
						<div className="overflow-x-auto">
							<Table className="table-fixed w-full">
								<THead>
									<Tr>
										<Th className="text-left sticky left-0 z-10 bg-inherit w-32">币种</Th>
										<Th className="text-left w-36">套利组合</Th>
										<Th className="text-left w-24">交易所</Th>
										<Th 
											className="text-right w-24 cursor-pointer"
											onClick={() => handleSort('funding_rate')}
										>
											<div className="flex items-center justify-end">
												资金费率
												{renderSortIcon('funding_rate')}
											</div>
										</Th>
										<Th 
											className="text-right w-24 cursor-pointer"
											onClick={() => handleSort('daily_return')}
										>
											<div className="flex items-center justify-end">
												日收益
												{renderSortIcon('daily_return')}
											</div>
										</Th>
										<Th className="text-right w-28">三日累计费率</Th>
										<Th className="text-right w-24">3日收益</Th>
										<Th 
											className="text-right w-24 cursor-pointer"
											onClick={() => handleSort('annual_rate')}
										>
											<div className="flex items-center justify-end">
												年化费率
												{renderSortIcon('annual_rate')}
											</div>
										</Th>
										<Th 
											className="text-right w-24 cursor-pointer"
											onClick={() => handleSort('annual_return')}
										>
											<div className="flex items-center justify-end">
												年收益
												{renderSortIcon('annual_return')}
											</div>
										</Th>
										<Th className="text-center w-16">评分</Th>
										<Th className="text-center w-16">状态</Th>
										<Th className="text-left w-40">最后更新</Th>
										<Th className="text-center sticky right-0 z-10 bg-inherit w-32">操作</Th>
									</Tr>
								</THead>
								<TBody>
									{filteredAndSortedData.length > 0 ? (
										filteredAndSortedData.map((item) => {
											const timeDiff = getTimeDifference(item.last_update);
											const isSelected = selectedRow === item.id;
											
											return (
												<Tr 
													key={item.id}
													className={`group cursor-pointer transition-colors duration-150 hover:bg-gray-100 dark:hover:bg-gray-800 ${
														isSelected 
															? 'bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/30 dark:hover:bg-blue-900/50' 
															: ''
													}`}
													onClick={() => handleRowClick(item.id)}
												>
													<Td className={`text-left sticky left-0 z-10 whitespace-nowrap overflow-hidden text-ellipsis ${
														isSelected 
															? 'bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/30 dark:hover:bg-blue-900/50' 
															: 'bg-inherit group-hover:bg-gray-100 dark:group-hover:bg-gray-800'
													}`}>
														<div className="flex items-center">
															<div className="w-4 mr-2 flex-shrink-0">
																{isSelected ? (
																	<Icon icon="HeroChevronRight" className="h-4 w-4 text-blue-500" />
																) : (
																	<div className="h-4 w-4 rounded-full bg-gray-200 dark:bg-gray-700 opacity-0 group-hover:opacity-100 transition-opacity duration-150"></div>
																)}
															</div>
															<span className="font-semibold">{item.symbol}</span>
														</div>
													</Td>
													<Td className="text-left whitespace-nowrap">{item.pair}</Td>
													<Td className="text-left whitespace-nowrap">{item.exchange}</Td>
													<Td className="text-right whitespace-nowrap">
														{(item.funding_rate * 100).toFixed(4)}%
													</Td>
													<Td className="text-right whitespace-nowrap">
														{(item.daily_return * 100).toFixed(4)}%
													</Td>
													<Td className="text-right whitespace-nowrap">
														{(item.three_day_cumulative * 100).toFixed(4)}%
													</Td>
													<Td className="text-right whitespace-nowrap">
														${(filters.positionSize * item.three_day_return).toFixed(2)}
													</Td>
													<Td className="text-right whitespace-nowrap">
														{(item.annual_rate * 100).toFixed(2)}%
													</Td>
													<Td className="text-right whitespace-nowrap">
														${(filters.positionSize * item.annual_return).toFixed(2)}
													</Td>
													<Td className="text-center whitespace-nowrap">
														<div className={`font-semibold ${
															item.score >= 90 ? 'text-emerald-500' : 
															item.score >= 80 ? 'text-blue-500' : 
															item.score >= 70 ? 'text-amber-500' : 'text-red-500'
														}`}>
															{item.score}
														</div>
													</Td>
													<Td className="text-center whitespace-nowrap">
														{getStatusBadge(item.status)}
													</Td>
													<Td className="text-left whitespace-nowrap">
														<div className="flex items-center gap-2">
															<span>{formatTimestamp(item.last_update)}</span>
															<Tooltip text={timeDiff.text}>
																<span className={`text-xs ${timeDiff.isStale ? 'text-red-500' : 'text-gray-500 dark:text-gray-400'}`}>
																	{timeDiff.text}
																</span>
															</Tooltip>
														</div>
													</Td>
													<Td className={`text-center sticky right-0 z-10 ${
														isSelected 
															? 'bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/30 dark:hover:bg-blue-900/50' 
															: 'bg-inherit group-hover:bg-gray-100 dark:group-hover:bg-gray-800'
													}`}>
														<div className="flex gap-1 justify-center">
															<Button
																icon="HeroCurrencyDollar"
																color="emerald"
																variant="outline"
																size="xs"
																className="px-1 hover:bg-emerald-100 dark:hover:bg-emerald-800/50"
																title="执行交易"
																onClick={(e) => handleTrade(item.id, e)}
															/>
															<Button
																icon="HeroClipboardDocument"
																color="blue"
																variant="outline"
																size="xs"
																className="px-1 hover:bg-blue-100 dark:hover:bg-blue-800/50"
																title="添加到白名单"
																onClick={(e) => handleAddToWhitelist(item.id, e)}
															/>
															<Button
																icon="HeroInformationCircle"
																color="zinc"
																variant="outline"
																size="xs"
																className="px-1 hover:bg-zinc-100 dark:hover:bg-zinc-800/50"
																title="查看详情"
																onClick={(e) => handleViewDetails(item.id, e)}
															/>
														</div>
													</Td>
												</Tr>
											);
										})
									) : (
										<Tr>
											<Td colSpan={13} className="text-center py-8 text-gray-400 dark:text-gray-500">
												{filters.search ? '未找到匹配的套利机会' : '暂无资金费率套利机会'}
											</Td>
										</Tr>
									)}
								</TBody>
							</Table>
						</div>
					</CardBody>
				</Card>

				{/* 说明卡片 */}
				<Card>
					<CardHeader>
						<CardTitle>资金费率套利说明</CardTitle>
					</CardHeader>
					<CardBody>
						<div className="space-y-4 text-gray-700">
							<p>
								<strong>资金费率套利</strong>是一种在加密货币衍生品市场中利用永续合约与现货市场之间价差的交易策略。
							</p>
							<p>
								此策略涉及同时在永续合约和现货市场建立反向头寸，通过收取资金费率获利，同时对冲价格波动风险。
							</p>
							<p>
								<strong>关键指标说明：</strong>
							</p>
							<ul className="list-disc list-inside space-y-2 ml-4">
								<li>
									<strong>资金费率：</strong>单个周期(通常为8小时)的资金费率
								</li>
								<li>
									<strong>日收益：</strong>基于当前资金费率计算的24小时收益
								</li>
								<li>
									<strong>三日累计费率：</strong>过去三天的累计资金费率
								</li>
								<li>
									<strong>年化费率：</strong>将当前资金费率年化后的预期收益率
								</li>
								<li>
									<strong>年收益：</strong>基于投入资金和年化费率计算的预期年化收益
								</li>
								<li>
									<strong>评分：</strong>综合考虑资金费率、流动性、币种风险等因素的综合评分
								</li>
							</ul>
							<p>
								<strong>风险提示：</strong>历史资金费率不代表未来表现，市场波动可能导致费率变化。始终保持风险管理，并考虑流动性和交易成本。
							</p>
						</div>
					</CardBody>
				</Card>
			</div>
		</PageWrapper>
	);
};

export default FundingRateArbitragePage; 