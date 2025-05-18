'use client';

import React, { useState, useEffect } from 'react';
import Card, { CardBody } from '../../../../../components/ui/Card';
import PageWrapper from '../../../../../components/layouts/PageWrapper/PageWrapper';
import Button from '../../../../../components/ui/Button';
import Table, { THead, TBody, Tr, Th, Td } from '../../../../../components/ui/Table';
import Badge from '../../../../../components/ui/Badge';
import Dropdown, { DropdownItem, DropdownMenu, DropdownToggle } from '../../../../../components/ui/Dropdown';

// 模拟数据 - 实际项目中应该从API获取
const mockSignalsData = [
	{
		id: '1',
		pair: 'BTC-USDT',
		exchange: 'OKX',
		type: 'open',
		action: 'buy_spot_sell_swap',
		funding_rate: '0.0085',
		basis: '0.0012',
		opportunity_score: '92',
		timestamp: '2023-10-25 08:30:45',
		status: 'new',
	},
	{
		id: '2',
		pair: 'ETH-USDT',
		exchange: 'OKX',
		type: 'open',
		action: 'buy_spot_sell_swap',
		funding_rate: '0.0076',
		basis: '0.0008',
		opportunity_score: '87',
		timestamp: '2023-10-25 08:28:12',
		status: 'executed',
	},
	{
		id: '3',
		pair: 'SOL-USDT',
		exchange: 'OKX',
		type: 'close',
		action: 'sell_spot_buy_swap',
		funding_rate: '0.0022',
		basis: '-0.0003',
		opportunity_score: 'N/A',
		timestamp: '2023-10-25 08:15:32',
		status: 'executed',
	},
	{
		id: '4',
		pair: 'XRP-USDT',
		exchange: 'OKX',
		type: 'open',
		action: 'buy_spot_sell_swap',
		funding_rate: '0.0065',
		basis: '0.0009',
		opportunity_score: '79',
		timestamp: '2023-10-25 08:10:18',
		status: 'rejected',
	},
];

const FundingRateSignalsPage = () => {
	const [signalsData, setSignalsData] = useState(mockSignalsData);
	const [activeFilter, setActiveFilter] = useState('all'); // 'all', 'new', 'executed', 'rejected'

	// 根据筛选条件过滤数据
	const filteredData = activeFilter === 'all' 
		? signalsData 
		: signalsData.filter(signal => signal.status === activeFilter);

	// 处理执行信号操作
	const handleExecuteSignal = (id: string) => {
		setSignalsData(prev => 
			prev.map(signal => 
				signal.id === id 
					? { ...signal, status: 'executed' } 
					: signal
			)
		);
	};

	// 处理拒绝信号操作
	const handleRejectSignal = (id: string) => {
		setSignalsData(prev => 
			prev.map(signal => 
				signal.id === id 
					? { ...signal, status: 'rejected' } 
					: signal
			)
		);
	};

	// 获取动作显示文本
	const getActionText = (action: string): string => {
		switch(action) {
			case 'buy_spot_sell_swap':
				return '买入现货/卖出合约';
			case 'sell_spot_buy_swap':
				return '卖出现货/买入合约';
			default:
				return action;
		}
	};

	// 获取状态Badge
	const getStatusBadge = (status: string) => {
		let color = 'blue';
		let text = '';
		
		switch(status) {
			case 'new':
				color = 'blue';
				text = '新信号';
				break;
			case 'executed':
				color = 'emerald';
				text = '已执行';
				break;
			case 'rejected':
				color = 'red';
				text = '已拒绝';
				break;
			default:
				color = 'amber';
				text = status;
		}
		
		return <Badge color={color} className="text-xs">{text}</Badge>;
	};

	return (
		<PageWrapper>
			<div className="flex flex-col gap-4">
				<div className="flex justify-between items-center">
					<h1 className="text-2xl font-bold">交易信号</h1>
					<div className="flex gap-2">
						<Dropdown>
							<DropdownToggle>
								<Button 
									variant="outline"
									color="blue"
									icon="HeroFunnel">
									{
										activeFilter === 'all' ? '全部信号' :
										activeFilter === 'new' ? '新信号' :
										activeFilter === 'executed' ? '已执行' :
										'已拒绝'
									}
								</Button>
							</DropdownToggle>
							<DropdownMenu placement="bottom-end">
								<DropdownItem onClick={() => setActiveFilter('all')}>
									全部信号
								</DropdownItem>
								<DropdownItem onClick={() => setActiveFilter('new')}>
									新信号
								</DropdownItem>
								<DropdownItem onClick={() => setActiveFilter('executed')}>
									已执行
								</DropdownItem>
								<DropdownItem onClick={() => setActiveFilter('rejected')}>
									已拒绝
								</DropdownItem>
							</DropdownMenu>
						</Dropdown>
						<Button
							variant="solid"
							color="blue"
							icon="HeroArrowPath">
							刷新
						</Button>
					</div>
				</div>

				<Card>
					<CardBody>
						<Table>
							<THead>
								<Tr>
									<Th>时间</Th>
									<Th>交易对</Th>
									<Th>交易所</Th>
									<Th>类型</Th>
									<Th>操作</Th>
									<Th>资金费率</Th>
									<Th>基差</Th>
									<Th>机会评分</Th>
									<Th>状态</Th>
									<Th>操作</Th>
								</Tr>
							</THead>
							<TBody>
								{filteredData.map((signal) => (
									<Tr key={signal.id}>
										<Td className="whitespace-nowrap">{signal.timestamp}</Td>
										<Td>
											<div className="font-bold">{signal.pair}</div>
										</Td>
										<Td>{signal.exchange}</Td>
										<Td>
											<Badge
												color={signal.type === 'open' ? 'emerald' : 'amber'}
												className="text-xs">
												{signal.type === 'open' ? '开仓' : '平仓'}
											</Badge>
										</Td>
										<Td>{getActionText(signal.action)}</Td>
										<Td className="text-right">{parseFloat(signal.funding_rate) * 100}%</Td>
										<Td>
											<div className={`text-right ${parseFloat(signal.basis) >= 0 ? 'text-success-500' : 'text-danger-500'}`}>
												{(parseFloat(signal.basis) * 100).toFixed(4)}%
											</div>
										</Td>
										<Td>{signal.opportunity_score}</Td>
										<Td>{getStatusBadge(signal.status)}</Td>
										<Td>
											{signal.status === 'new' ? (
												<div className="flex gap-2">
													<Button
														variant="outline"
														color="emerald"
														size="sm"
														icon="HeroCheck"
														onClick={() => handleExecuteSignal(signal.id)}>
														执行
													</Button>
													<Button
														variant="outline"
														color="red"
														size="sm"
														icon="HeroXMark"
														onClick={() => handleRejectSignal(signal.id)}>
														拒绝
													</Button>
												</div>
											) : (
												<div className="text-gray-400">无操作</div>
											)}
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

export default FundingRateSignalsPage; 