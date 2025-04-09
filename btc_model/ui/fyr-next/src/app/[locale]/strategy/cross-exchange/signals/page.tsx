'use client';

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import PageWrapper from '@/components/layouts/PageWrapper/PageWrapper';
import { useTranslation } from 'react-i18next';
import Card, { CardBody, CardHeader, CardHeaderChild } from '@/components/ui/Card';
import Table, { THead, TBody, Tr, Th, Td } from '@/components/ui/Table';
import Button from '@/components/ui/Button';
import Icon from '@/components/icon/Icon';
import Badge from '@/components/ui/Badge';
import Tooltip from '@/components/ui/Tooltip';
import Tabs, { TabItem } from '@/components/ui/Tabs';

interface Signal {
	pair?: string;
	symbol: string;  // 兼容两种不同的属性名
	exchange_1: string;
	exchange_2: string;
	exchange_1_position?: number;
	exchange_2_position?: number;
	exchange_1_bid_price?: number;
	exchange_1_bid_volume?: number;
	exchange_1_ask_price?: number;
	exchange_1_ask_volume?: number;
	exchange_1_updatetime?: string;
	exchange_2_bid_price?: number;
	exchange_2_bid_volume?: number;
	exchange_2_ask_price?: number;
	exchange_2_ask_volume?: number;
	exchange_2_updatetime?: string;
	hedge_exchange?: string;
	hedge_position?: number;
	spread: number;  // 使用新的spread字段而不是price_diff
	signal?: string;  // buy, sell信号类型
	volume: number;
	status: string;
	timestamp: string;
	id?: string;  // 可选的信号ID
}

// 添加排序相关类型
type SortColumn = 'symbol' | 'price_diff' | 'timestamp';
type SortDirection = 'asc' | 'desc';

// 新增接口定义
interface Order {
	id: string;
	symbol: string;
	side: 'buy' | 'sell';
	price: number;
	volume: number;
	status: string;
	exchange: string;
	timestamp: string;
}

interface Position {
	id: string;
	symbol: string;
	exchange: string;
	volume: number;
	entryPrice: number;
	currentPrice: number;
	pnl: number;
	status: string;
	timestamp: string;
}

const CrossExchangeSignalsPage = () => {
	const { t } = useTranslation();
	const [signals, setSignals] = useState<Signal[]>([]);
	const [isWsConnected, setIsWsConnected] = useState(false);
	const [isApiConnected, setIsApiConnected] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const wsRef = useRef<WebSocket | null>(null);
	const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
	const reconnectCountRef = useRef<number>(0);
	const MAX_RECONNECT_ATTEMPTS = 10;
	const RECONNECT_INTERVAL = 3000; // 3秒
	const isComponentMounted = useRef(true);

	// 添加标签页状态
	const [activeTab, setActiveTab] = useState<string>('signals');

	// 添加订单和持仓数据状态
	const [pendingOrders, setPendingOrders] = useState<Order[]>([]);
	const [completedOrders, setCompletedOrders] = useState<Order[]>([]);
	const [positions, setPositions] = useState<Position[]>([]);

	// 添加选中行状态
	const [selectedRow, setSelectedRow] = useState<string | null>(null);

	// 添加排序状态
	const [sortColumn, setSortColumn] = useState<SortColumn>('timestamp');
	const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
	
	// 当前时间，用于计算时间差
	const [currentTime, setCurrentTime] = useState(new Date());

	// 清理函数 - 关闭WebSocket和清除计时器
	const cleanup = () => {
		if (wsRef.current) {
			// 临时移除onclose处理程序，防止触发重连逻辑
			wsRef.current.onclose = null;
			wsRef.current.close();
			wsRef.current = null;
		}

		if (reconnectTimerRef.current) {
			clearTimeout(reconnectTimerRef.current);
			reconnectTimerRef.current = null;
		}
	};

	// 检查REST API服务是否可用
	const checkApiStatus = useCallback(async () => {
		try {
			const response = await fetch('http://localhost:8002/health', { 
				method: 'GET',
				headers: { 'Content-Type': 'application/json' }
			});
			
			if (response.ok) {
				setIsApiConnected(true);
				setError(null);
			} else {
				setIsApiConnected(false);
			}
		} catch (error) {
			console.error('API连接检查失败:', error);
			setIsApiConnected(false);
		}
	}, []);

	// 初始化WebSocket连接
	const initWebSocket = useCallback(() => {
		// 先清理之前的连接和计时器
		cleanup();

		// 如果组件已卸载，不要创建新连接
		if (!isComponentMounted.current) return;

		try {
			console.log('正在初始化WebSocket连接...');
			const ws = new WebSocket('ws://localhost:8001/ws/arbitrage-signals');
			wsRef.current = ws;

			ws.onopen = () => {
				if (isComponentMounted.current) {
					setIsWsConnected(true);
					setError(null);
					console.log('WebSocket已连接');
					reconnectCountRef.current = 0; // 重置重连计数
				}
			};

			ws.onmessage = (event) => {
				if (!isComponentMounted.current) return;
				
				try {
					const data = JSON.parse(event.data);
					handleWebSocketMessage(data);
				} catch (error) {
					console.error('处理WebSocket消息出错:', error);
				}
			};

			ws.onclose = (event) => {
				if (!isComponentMounted.current) return;

				console.log(`WebSocket连接关闭: ${event.code} ${event.reason}`);
				setIsWsConnected(false);
				
				// 如果不是手动关闭，则尝试重连
				if (event.code !== 1000) {
					handleReconnect();
				}
			};

			ws.onerror = (error) => {
				if (!isComponentMounted.current) return;

				console.error('WebSocket连接错误:', error);
				setIsWsConnected(false);
				setError('WebSocket连接错误，正在尝试重连...');
			};
		} catch (error) {
			if (isComponentMounted.current) {
				console.error('创建WebSocket连接出错:', error);
				setIsWsConnected(false);
				setError(`创建WebSocket连接出错: ${error}`);
				handleReconnect();
			}
		}
	}, []);

	// 处理WebSocket重连
	const handleReconnect = useCallback(() => {
		if (!isComponentMounted.current) return;
		
		// 如果已经达到最大重试次数，停止重连
		if (reconnectCountRef.current >= MAX_RECONNECT_ATTEMPTS) {
			console.error(`已达到最大重连尝试次数(${MAX_RECONNECT_ATTEMPTS})，停止重连`);
			setError(`连接服务器失败，已尝试${MAX_RECONNECT_ATTEMPTS}次。请检查服务器状态或手动刷新页面。`);
			return;
		}
		
		reconnectCountRef.current += 1;
		
		// 计算重连时间间隔（指数退避）
		const delay = Math.min(RECONNECT_INTERVAL * Math.pow(1.5, reconnectCountRef.current - 1), 30000);
		
		console.log(`WebSocket ${reconnectCountRef.current}/${MAX_RECONNECT_ATTEMPTS} 次重连尝试，${delay}ms后重连`);
		setError(`WebSocket连接断开，${Math.round(delay/1000)}秒后尝试第${reconnectCountRef.current}次重连...`);
		
		// 设置重连定时器
		if (reconnectTimerRef.current) {
			clearTimeout(reconnectTimerRef.current);
		}
		
		reconnectTimerRef.current = setTimeout(() => {
			initWebSocket();
		}, delay);
	}, [initWebSocket]);

	// 手动刷新连接
	const refreshConnection = useCallback(() => {
		console.log('手动刷新连接');
		reconnectCountRef.current = 0; // 重置重连计数
		initWebSocket();
		checkApiStatus();
	}, [initWebSocket, checkApiStatus]);

	// 初始化
	useEffect(() => {
		// 设置组件挂载状态
		isComponentMounted.current = true;
		
		// 初始化WebSocket和检查API
		initWebSocket();
		checkApiStatus();
		
		// 定期检查API状态
		const apiCheckInterval = setInterval(() => {
			checkApiStatus();
		}, 30000); // 每30秒检查一次

		// 组件卸载时清理
		return () => {
			isComponentMounted.current = false;
			clearInterval(apiCheckInterval);
			cleanup();
		};
	}, [initWebSocket, checkApiStatus]);

	// 处理排序
	const handleSort = (column: SortColumn) => {
		if (sortColumn === column) {
			// 如果点击的是当前排序列，切换排序方向
			setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
		} else {
			// 如果点击的是新列，设置为该列降序排序
			setSortColumn(column);
			setSortDirection('desc');
		}
	};

	// 获取排序的信号数据
	const sortedSignals = useMemo(() => {
		if (!signals.length) return [];
		
		return [...signals].sort((a, b) => {
			let valueA, valueB;
			
			switch (sortColumn) {
				case 'symbol':
					valueA = (a.symbol || a.pair || '').toLowerCase();
					valueB = (b.symbol || b.pair || '').toLowerCase();
					break;
				case 'price_diff':
					// 处理不同格式的价差
					valueA = typeof a.spread === 'number' ? a.spread : 
						parseFloat(String(a.spread).replace('%', '')) / 100;
					valueB = typeof b.spread === 'number' ? b.spread : 
						parseFloat(String(b.spread).replace('%', '')) / 100;
					break;
				case 'timestamp':
				default:
					valueA = new Date(a.timestamp).getTime();
					valueB = new Date(b.timestamp).getTime();
					break;
			}
			
			// 根据排序方向返回结果
			if (sortDirection === 'asc') {
				return valueA > valueB ? 1 : -1;
			} else {
				return valueA < valueB ? 1 : -1;
			}
		});
	}, [signals, sortColumn, sortDirection]);

	// 处理从WebSocket接收到的消息
	const handleWebSocketMessage = (data: any) => {
		if (!data || !data.type) return;
		
		switch (data.type) {
			case 'all_signals':
				// 接收全量信号，替换当前所有信号
				console.log(`接收到全量信号: ${data.data.length}个`);
				setSignals(data.data);
				break;
				
			case 'new_signals':
				// 接收增量信号，添加或更新现有信号
				console.log(`接收到新信号: ${data.data.length}个`);
				setSignals(prevSignals => {
					// 创建信号ID到信号的映射
					const signalMap = new Map(prevSignals.map(s => [getSignalId(s), s]));
					
					// 更新或添加新信号
					data.data.forEach((signal: Signal) => {
						signalMap.set(getSignalId(signal), signal);
					});
					
					// 将Map转换回数组
					return Array.from(signalMap.values());
				});
				break;
				
		case 'signals':
				// 兼容旧格式 - 直接设置信号
				console.log(`接收到信号数据: ${data.data.length}个`);
				setSignals(data.data);
				break;
				
			case 'pending_orders':
				// 接收委托订单
				console.log(`接收到委托订单: ${data.data.length}个`);
				setPendingOrders(data.data);
				break;
				
			case 'completed_orders':
				// 接收成交订单
				console.log(`接收到成交订单: ${data.data.length}个`);
				setCompletedOrders(data.data);
				break;
				
			case 'positions':
				// 接收持仓信息
				console.log(`接收到策略持仓: ${data.data.length}个`);
				setPositions(data.data);
				break;
				
			case 'heartbeat':
				// 心跳包，不需要处理
				console.log('接收到心跳包');
				break;
				
			default:
				console.warn(`未知消息类型: ${data.type}`);
		}
	};

	// 获取信号的唯一标识
	const getSignalId = (signal: Signal): string => {
		if (signal.id) return signal.id;
		return signal.symbol || signal.pair || `${signal.exchange_1}-${signal.exchange_2}-${signal.timestamp}`;
	};

	// 更新当前时间，每秒更新一次
	useEffect(() => {
		const intervalId = setInterval(() => {
			setCurrentTime(new Date());
		}, 1000);
		
		return () => clearInterval(intervalId);
	}, []);

	// 处理信号状态
	const getStatusBadge = (status: string) => {
		switch (status) {
			case 'active':
			case 'open':
				return (
					<Badge color='emerald' variant='outline'>
						{t('active')}
					</Badge>
				);
			case 'expired':
			case 'closed':
				return (
					<Badge color='red' variant='outline'>
						{t('expired')}
					</Badge>
				);
			default:
				return (
					<Badge color='zinc' variant='outline'>
						{t('unknown')}
					</Badge>
				);
		}
	};

	// 格式化价差显示
	const formatPriceDiff = (priceDiff: any): string => {
		// 处理不同格式的价差值
		if (typeof priceDiff === 'number') {
			return `${(priceDiff * 100).toFixed(4)}%`;
		}
		// 如果已经是字符串且包含%，直接返回
		if (typeof priceDiff === 'string' && priceDiff.includes('%')) {
			return priceDiff;
		}
		// 其他情况，尝试转换为数字并格式化
		try {
			const numValue = parseFloat(String(priceDiff));
			if (!isNaN(numValue)) {
				return `${(numValue * 100).toFixed(4)}%`;
			}
		} catch (e) {}
		
		// 无法处理时返回原值
		return String(priceDiff);
	};

	// 格式化时间显示
	const formatTimestamp = (timestamp: string): string => {
		try {
			if (!timestamp) return '-';
			// 处理Unix时间戳
			if (!isNaN(Number(timestamp))) {
				const date = new Date(Number(timestamp) * 1000);
				return date.toLocaleString();
			}
			// 尝试解析日期字符串
			const date = new Date(timestamp);
			if (!isNaN(date.getTime())) {
				return date.toLocaleString();
			}
			// 默认返回原始值
			return timestamp;
		} catch (e) {
			return timestamp;
		}
	};

	// 计算时间差
	const getTimeDifference = (timestamp: string): { text: string; isStale: boolean } => {
		try {
			if (!timestamp) return { text: '-', isStale: false };
			
			let date: Date;
			
			// 处理Unix时间戳
			if (!isNaN(Number(timestamp))) {
				date = new Date(Number(timestamp) * 1000);
			} else {
				// 尝试解析日期字符串
				date = new Date(timestamp);
			}
			
			if (isNaN(date.getTime())) {
				return { text: '-', isStale: false };
			}
			
			const diffMs = Math.max(0, currentTime.getTime() - date.getTime());
			const diffSec = Math.floor(diffMs / 1000);
			
			if (diffSec < 60) {
				return { text: `${diffSec}秒前`, isStale: false };
			} else if (diffSec < 3600) {
				const mins = Math.floor(diffSec / 60);
				return { text: `${mins}分钟前`, isStale: diffSec >= 60 }; // 1分钟以上标记为过期
			} else if (diffSec < 86400) {
				const hours = Math.floor(diffSec / 3600);
				return { text: `${hours}小时前`, isStale: true };
			} else {
				const days = Math.floor(diffSec / 86400);
				return { text: `${days}天前`, isStale: true };
			}
		} catch (e) {
			return { text: '-', isStale: false };
		}
	};

	// 渲染排序图标
	const renderSortIcon = (column: SortColumn) => {
		if (sortColumn !== column) {
			return <Icon icon="HeroArrowsUpDown" className="ml-1 inline-block h-4 w-4 text-gray-400" />;
		}
		
		return sortDirection === 'asc' 
			? <Icon icon="HeroArrowUp" className="ml-1 inline-block h-4 w-4 text-blue-500" />
			: <Icon icon="HeroArrowDown" className="ml-1 inline-block h-4 w-4 text-blue-500" />;
	};

	// 处理行点击
	const handleRowClick = (signalId: string) => {
		setSelectedRow(prevSelected => prevSelected === signalId ? null : signalId);
	};

	// 格式化订单状态
	const getOrderStatusBadge = (status: string) => {
		switch (status.toLowerCase()) {
			case 'filled':
			case 'complete':
				return (
					<Badge color='emerald' variant='outline'>
						{t('已成交')}
					</Badge>
				);
			case 'partial':
			case 'partially_filled':
				return (
					<Badge color='amber' variant='outline'>
						{t('部分成交')}
					</Badge>
				);
			case 'open':
			case 'pending':
				return (
					<Badge color='blue' variant='outline'>
						{t('挂单中')}
					</Badge>
				);
			case 'canceled':
			case 'cancelled':
				return (
					<Badge color='red' variant='outline'>
						{t('已取消')}
					</Badge>
				);
			default:
				return (
					<Badge color='zinc' variant='outline'>
						{status}
					</Badge>
				);
		}
	};

	// 格式化订单方向
	const getOrderSideBadge = (side: string) => {
		return side.toLowerCase() === 'buy' ? (
			<Badge color='emerald'>{t('买入')}</Badge>
		) : (
			<Badge color='red'>{t('卖出')}</Badge>
		);
	};

	// 格式化持仓状态
	const getPositionStatusBadge = (status: string) => {
		switch (status.toLowerCase()) {
			case 'open':
			case 'active':
				return (
					<Badge color='emerald' variant='outline'>
						{t('持有中')}
					</Badge>
				);
			case 'closing':
				return (
					<Badge color='amber' variant='outline'>
						{t('平仓中')}
					</Badge>
				);
			case 'closed':
				return (
					<Badge color='zinc' variant='outline'>
						{t('已平仓')}
					</Badge>
				);
			default:
				return (
					<Badge color='zinc' variant='outline'>
						{status}
					</Badge>
				);
		}
	};

	// 格式化盈亏显示
	const formatPnL = (pnl: number) => {
		const formattedPnL = pnl.toFixed(2);
		return pnl >= 0 ? (
			<span className="text-emerald-500">+{formattedPnL}</span>
		) : (
			<span className="text-red-500">{formattedPnL}</span>
		);
	};

	// 获取显示价格 - 根据信号类型返回相应的买卖价格
	const getDisplayPrices = (signal: Signal) => {
		// 默认显示价格
		let exchange1Price = signal.exchange_1_bid_price;
		let exchange2Price = signal.exchange_2_ask_price;
		let exchange1Volume = signal.exchange_1_bid_volume;
		let exchange2Volume = signal.exchange_2_ask_volume;
		
		// 如果是卖出信号，则显示相反的价格
		if (signal.signal && signal.signal.toLowerCase() === 'sell') {
			exchange1Price = signal.exchange_1_ask_price;
			exchange2Price = signal.exchange_2_bid_price;
			exchange1Volume = signal.exchange_1_ask_volume;
			exchange2Volume = signal.exchange_2_bid_volume;
		}
		
		return {
			exchange1Price,
			exchange2Price,
			exchange1Volume,
			exchange2Volume
		};
	};

	// 添加执行套利的函数
	const executeArbitrage = async (signal: Signal, type: 'hedge' | 'arbitrage') => {
		try {
			// 获取信号ID
			const signalId = signal.id || getSignalId(signal);
			
			// 构建请求参数
			const params = {
				symbol: signal.symbol || signal.pair,
				exchange_1: signal.exchange_1,
				exchange_2: signal.exchange_2,
				spread: signal.spread,
				volume: signal.volume,
				signal_id: signalId,
				type: type // 添加类型参数
			};

			// 发送执行请求到后端API
			const response = await fetch('http://localhost:8002/api/strategy/exchange-arbitrage/execute', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify(params),
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.message || '执行失败');
			}

			const result = await response.json();
			console.log('套利执行结果:', result);
			
			// 可以添加成功消息提示
			// 这里示例直接使用alert, 实际项目中应该使用更友好的UI组件
			const actionText = type === 'hedge' ? '创建对冲仓位' : '套利下单';
			alert(t(`${actionText}已执行，请查看委托订单`));
			
			// 切换到委托订单标签页查看结果
			setActiveTab('pending_orders');
			
		} catch (error) {
			console.error('执行出错:', error);
			alert(t('执行失败: ') + (error instanceof Error ? error.message : String(error)));
		}
	};

	return (
		<PageWrapper>
			<div className='flex h-full w-full flex-col gap-4 p-2'>
				<Card>
					<CardHeader>
						<CardHeaderChild>
							<div className='text-lg font-semibold'>{t('跨所套利信号')}</div>
						</CardHeaderChild>
						<CardHeaderChild>
							<div className='flex items-center gap-2'>
								{error && (
									<div className='text-red-500 text-sm'>{error}</div>
								)}
								<div className='flex items-center gap-1'>
									<Badge
										color={isWsConnected ? 'emerald' : 'red'}
										variant='outline'
										className='flex items-center gap-1'>
										<Icon icon='HeroSignal' className='h-3 w-3' />
										{isWsConnected ? t('数据连接') : t('数据断开')}
									</Badge>
									<Badge
										color={isApiConnected ? 'emerald' : 'red'}
										variant='outline'
										className='flex items-center gap-1'>
										<Icon icon='HeroServerStack' className='h-3 w-3' />
										{isApiConnected ? t('交易连接') : t('交易断开')}
									</Badge>
								</div>
								<div className='text-sm text-gray-500'>
									{t('信号数')}：{signals.length}
								</div>
								<Button
									icon='HeroArrowPath'
									onClick={refreshConnection}>
									{t('刷新')}
								</Button>
							</div>
						</CardHeaderChild>
					</CardHeader>
					<CardBody>
						<Tabs activeTabId={activeTab} onTabChange={setActiveTab}>
							<TabItem id="signals" title="信号">
								<div className="overflow-x-auto">
									<Table className="table-fixed w-full">
										<THead>
											<Tr>
												<Th 
													className='text-left sticky left-0 z-10 bg-inherit w-28 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800' 
													onClick={() => handleSort('symbol')}
												>
													{t('symbol')}
													{renderSortIcon('symbol')}
												</Th>
												<Th className='text-left w-28 whitespace-nowrap'>
													{t('exchage_1')}
												</Th>
												<Th className='text-left w-28 whitespace-nowrap'>
													{t('exchage_2')}
												</Th>
												<Th className='text-center w-16'>{t('signal')}</Th>
												<Th 
													className='text-right w-20 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800'
													onClick={() => handleSort('price_diff')}
												>
													{t('spread')}
													{renderSortIcon('price_diff')}
												</Th>
												<Th className='text-right w-16'>{t('volume')}</Th>
												<Th className='text-left w-16'>{t('status')}</Th>
												<Th 
													className='text-left w-52 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 whitespace-nowrap'
													onClick={() => handleSort('timestamp')}
												>
													{t('updatetime')}
													{renderSortIcon('timestamp')}
												</Th>
												<Th className='text-center sticky right-0 z-10 bg-inherit w-24'>{t('operation')}</Th>
											</Tr>
										</THead>
										<TBody>
											{sortedSignals.length > 0 ? (
												sortedSignals.map((signal, index) => {
													const timeDiff = getTimeDifference(signal.timestamp);
													const signalId = getSignalId(signal) || index.toString();
													const isSelected = selectedRow === signalId;
													
													return (
														<Tr 
															key={signalId}
															className={`group cursor-pointer transition-colors duration-150 hover:bg-gray-100 dark:hover:bg-gray-800 ${
																isSelected 
																	? 'bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/30 dark:hover:bg-blue-900/50' 
																	: ''
															}`}
															onClick={() => handleRowClick(signalId)}
														>
															<Td className={`text-left sticky left-0 z-10 w-28 whitespace-nowrap overflow-hidden text-ellipsis ${
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
																	<span className="truncate">{signal.symbol || signal.pair}</span>
																</div>
															</Td>
															<Td className='text-left w-28 whitespace-nowrap'>
																<div className="flex items-center justify-between">
																	<span>{signal.exchange_1}</span>
																	{signal.exchange_1_position !== undefined && (
																		<span className={`ml-2 ${signal.exchange_1_position >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
																			({signal.exchange_1_position.toFixed(4)})
																		</span>
																	)}
																</div>
															</Td>
															<Td className='text-left w-28 whitespace-nowrap'>
																<div className="flex items-center justify-between">
																	<span>{signal.exchange_2}</span>
																	{signal.exchange_2_position !== undefined && (
																		<span className={`ml-2 ${signal.exchange_2_position >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
																			({signal.exchange_2_position.toFixed(4)})
																		</span>
																	)}
																</div>
															</Td>
															<Td className='text-center w-16 whitespace-nowrap'>
																{signal.signal === 'buy' ? (
																	<Badge color='emerald'>{t('买入')}</Badge>
																) : (
																	<Badge color='red'>{t('卖出')}</Badge>
																)}
															</Td>
															<Td className='text-right w-20 font-medium text-emerald-500 whitespace-nowrap'>
																{(() => {
																	const prices = getDisplayPrices(signal);
																	return (
																		<Tooltip text={`${signal.exchange_1}: ${prices.exchange1Price?.toFixed(4) || '?'} (${prices.exchange1Volume?.toFixed(4) || '?'})\n${signal.exchange_2}: ${prices.exchange2Price?.toFixed(4) || '?'} (${prices.exchange2Volume?.toFixed(4) || '?'})\n对冲交易所: ${signal.hedge_exchange || '无'}\n对冲持仓: ${signal.hedge_position !== undefined ? signal.hedge_position.toFixed(4) : '?'}\n信号: ${signal.signal || '未知'}\n差价: ${formatPriceDiff(signal.spread)}`}>
																			<div className="flex flex-col items-end">
																				<div>{formatPriceDiff(signal.spread)}</div>
																				<div className="text-xs text-gray-500">
																					{prices.exchange1Price?.toFixed(5) || '?'} / {prices.exchange2Price?.toFixed(5) || '?'}
																				</div>
																			</div>
																		</Tooltip>
																	);
																})()}
															</Td>
															<Td className='text-right w-16 whitespace-nowrap'>
																{(() => {
																	const volume1 = signal.signal === 'buy' 
																		? signal.exchange_1_ask_volume 
																		: signal.exchange_1_bid_volume;
																	const volume2 = signal.signal === 'buy' 
																		? signal.exchange_2_bid_volume 
																		: signal.exchange_2_ask_volume;
																	const minVolume = Math.min(
																		volume1 || 0,
																		volume2 || 0
																	);
																	return (
																		<Tooltip text={`${signal.exchange_1}: ${volume1?.toFixed(4) || '?'}\n${signal.exchange_2}: ${volume2?.toFixed(4) || '?'}`}>
																			<div>{minVolume.toFixed(4)}</div>
																		</Tooltip>
																	);
																})()}
															</Td>
															<Td className='text-left w-16 whitespace-nowrap'>{getStatusBadge(signal.status)}</Td>
															<Td className='text-left w-52 whitespace-nowrap'>
																<div className="flex items-center gap-2">
																	<span>{formatTimestamp(signal.timestamp)}</span>
																	<Tooltip text={timeDiff.text}>
																		<span className={`text-xs ${timeDiff.isStale ? 'text-red-500' : 'text-gray-500 dark:text-gray-400'}`}>
																			{timeDiff.text}
																		</span>
																	</Tooltip>
																</div>
																<div className="text-xs text-gray-500">
																	{signal.exchange_1_updatetime ? new Date(signal.exchange_1_updatetime).toLocaleTimeString() : '?'} / {signal.exchange_2_updatetime ? new Date(signal.exchange_2_updatetime).toLocaleTimeString() : '?'}
																</div>
															</Td>
															<Td className={`text-center sticky right-0 z-10 w-24 ${
																isSelected 
																	? 'bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/30 dark:hover:bg-blue-900/50' 
																	: 'bg-inherit group-hover:bg-gray-100 dark:group-hover:bg-gray-800'
															}`}>
																<div className='flex gap-1 justify-center'>
																	<Button
																		icon='HeroArrowsRightLeft'
																		color='emerald'
																		variant='outline'
																		size='xs'
																		className='px-1 hover:bg-emerald-50'
																		title={t('创建对冲仓位')}
																		onClick={(e) => {
																			if (e) e.stopPropagation(); // 防止触发行点击
																			// 创建对冲仓位
																			executeArbitrage(signal, 'hedge');
																		}}
																	/>
																	<Button
																		icon='HeroCurrencyDollar'
																		color='amber'
																		variant='outline'
																		size='xs'
																		className='px-1 hover:bg-amber-50'
																		title={t('套利下单')}
																		onClick={(e) => {
																			if (e) e.stopPropagation(); // 防止触发行点击
																			// 执行套利
																			executeArbitrage(signal, 'arbitrage');
																		}}
																	/>
																	<Button
																		icon='HeroInformationCircle'
																		color='blue'
																		variant='outline'
																		size='xs'
																		className='px-1 hover:bg-blue-50'
																		title={t('详细')}
																		onClick={(e) => {
																			if (e) e.stopPropagation(); // 防止触发行点击
																			// 查看详细信息
																		}}
																	/>
																</div>
															</Td>
														</Tr>
													);
												})
											) : (
												<Tr>
													<Td colSpan={8} className='text-center py-8 text-gray-400 dark:text-gray-500'>
														{t('暂无套利信号')}
													</Td>
												</Tr>
											)}
										</TBody>
									</Table>
								</div>
							</TabItem>
							
							<TabItem id="pending_orders" title="委托订单">
								<div className="overflow-x-auto">
									<Table className="table-fixed w-full">
										<THead>
											<Tr>
												<Th className='text-left sticky left-0 z-10 bg-inherit w-40'>
													{t('order_id')}
												</Th>
												<Th className='text-left w-24'>{t('exchange')}</Th>
												<Th className='text-left w-24'>{t('symbol')}</Th>
												<Th className='text-center w-16'>{t('diretion')}</Th>
												<Th className='text-right w-24'>{t('price')}</Th>
												<Th className='text-right w-24'>{t('volume')}</Th>
												<Th className='text-left w-24'>{t('status')}</Th>
												<Th className='text-left w-40'>{t('updatetime')}</Th>
												<Th className='text-center sticky right-0 z-10 bg-inherit w-24'>{t('operation')}</Th>
											</Tr>
										</THead>
										<TBody>
											{pendingOrders.length > 0 ? (
												pendingOrders.map((order, index) => (
													<Tr key={order.id} className="hover:bg-gray-100 dark:hover:bg-gray-800">
														<Td className='text-left sticky left-0 z-10 bg-inherit w-40 truncate'>
															{order.id}
														</Td>
														<Td className='text-left w-24'>{order.exchange}</Td>
														<Td className='text-left w-24'>{order.symbol}</Td>
														<Td className='text-center w-16'>{getOrderSideBadge(order.side)}</Td>
														<Td className='text-right w-24'>{order.price}</Td>
														<Td className='text-right w-24'>{order.volume}</Td>
														<Td className='text-left w-24'>{getOrderStatusBadge(order.status)}</Td>
														<Td className='text-left w-40'>{formatTimestamp(order.timestamp)}</Td>
														<Td className='text-center sticky right-0 z-10 bg-inherit w-24'>
															<div className="flex gap-1 justify-center">
																<Button
																	icon='HeroXMark'
																	color='red'
																	variant='outline'
																	size='xs'
																	className='px-1'
																	title={t('取消')}
																	onClick={() => {
																		// 取消订单
																	}}
																/>
															</div>
														</Td>
													</Tr>
												))
											) : (
												<Tr>
													<Td colSpan={9} className='text-center py-8 text-gray-400 dark:text-gray-500'>
														{t('暂无委托订单')}
													</Td>
												</Tr>
											)}
										</TBody>
									</Table>
								</div>
							</TabItem>
							
							<TabItem id="completed_orders" title="成交订单">
								<div className="overflow-x-auto">
									<Table className="table-fixed w-full">
										<THead>
											<Tr>
												<Th className='text-left sticky left-0 z-10 bg-inherit w-40'>
													{t('订单ID')}
												</Th>
												<Th className='text-left w-24'>{t('交易所')}</Th>
												<Th className='text-left w-24'>{t('symbol')}</Th>
												<Th className='text-center w-16'>{t('方向')}</Th>
												<Th className='text-right w-24'>{t('价格')}</Th>
												<Th className='text-right w-24'>{t('数量')}</Th>
												<Th className='text-left w-24'>{t('状态')}</Th>
												<Th className='text-left w-40'>{t('时间')}</Th>
											</Tr>
										</THead>
										<TBody>
											{completedOrders.length > 0 ? (
												completedOrders.map((order, index) => (
													<Tr key={order.id} className="hover:bg-gray-100 dark:hover:bg-gray-800">
														<Td className='text-left sticky left-0 z-10 bg-inherit w-40 truncate'>
															{order.id}
														</Td>
														<Td className='text-left w-24'>{order.exchange}</Td>
														<Td className='text-left w-24'>{order.symbol}</Td>
														<Td className='text-center w-16'>{getOrderSideBadge(order.side)}</Td>
														<Td className='text-right w-24'>{order.price}</Td>
														<Td className='text-right w-24'>{order.volume}</Td>
														<Td className='text-left w-24'>{getOrderStatusBadge(order.status)}</Td>
														<Td className='text-left w-40'>{formatTimestamp(order.timestamp)}</Td>
													</Tr>
												))
											) : (
												<Tr>
													<Td colSpan={8} className='text-center py-8 text-gray-400 dark:text-gray-500'>
														{t('暂无成交订单')}
													</Td>
												</Tr>
											)}
										</TBody>
									</Table>
								</div>
							</TabItem>
							
							<TabItem id="positions" title="策略持仓">
								<div className="overflow-x-auto">
									<Table className="table-fixed w-full">
										<THead>
											<Tr>
												<Th className='text-left sticky left-0 z-10 bg-inherit w-40'>
													{t('持仓ID')}
												</Th>
												<Th className='text-left w-24'>{t('交易所')}</Th>
												<Th className='text-left w-24'>{t('symbol')}</Th>
												<Th className='text-right w-24'>{t('数量')}</Th>
												<Th className='text-right w-24'>{t('入场价')}</Th>
												<Th className='text-right w-24'>{t('当前价')}</Th>
												<Th className='text-right w-24'>{t('盈亏')}</Th>
												<Th className='text-left w-24'>{t('状态')}</Th>
												<Th className='text-left w-40'>{t('开仓时间')}</Th>
												<Th className='text-center sticky right-0 z-10 bg-inherit w-24'>{t('操作')}</Th>
											</Tr>
										</THead>
										<TBody>
											{positions.length > 0 ? (
												positions.map((position, index) => (
													<Tr key={position.id} className="hover:bg-gray-100 dark:hover:bg-gray-800">
														<Td className='text-left sticky left-0 z-10 bg-inherit w-40 truncate'>
															{position.id}
														</Td>
														<Td className='text-left w-24'>{position.exchange}</Td>
														<Td className='text-left w-24'>{position.symbol}</Td>
														<Td className='text-right w-24'>{position.volume}</Td>
														<Td className='text-right w-24'>{position.entryPrice}</Td>
														<Td className='text-right w-24'>{position.currentPrice}</Td>
														<Td className='text-right w-24'>{formatPnL(position.pnl)}</Td>
														<Td className='text-left w-24'>{getPositionStatusBadge(position.status)}</Td>
														<Td className='text-left w-40'>{formatTimestamp(position.timestamp)}</Td>
														<Td className='text-center sticky right-0 z-10 bg-inherit w-24'>
															<div className="flex gap-1 justify-center">
																<Button
																	icon='HeroArrowsRightLeft'
																	color='amber'
																	variant='outline'
																	size='xs'
																	className='px-1'
																	title={t('平仓')}
																	onClick={() => {
																		// 平仓操作
																	}}
																/>
															</div>
														</Td>
													</Tr>
												))
											) : (
												<Tr>
													<Td colSpan={10} className='text-center py-8 text-gray-400 dark:text-gray-500'>
														{t('暂无持仓')}
													</Td>
												</Tr>
											)}
										</TBody>
									</Table>
								</div>
							</TabItem>
						</Tabs>
					</CardBody>
				</Card>
			</div>
		</PageWrapper>
	);
};

export default CrossExchangeSignalsPage; 