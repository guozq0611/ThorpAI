'use client';

import React, { useState, useEffect } from 'react';
import Card, { CardBody } from '../../../../../components/ui/Card';
import PageWrapper from '../../../../../components/layouts/PageWrapper/PageWrapper';
import Button from '../../../../../components/ui/Button';
import Table, { THead, TBody, Tr, Th, Td } from '../../../../../components/ui/Table';
import Badge from '../../../../../components/ui/Badge';
import Icon from '../../../../../components/icon/Icon';

// 模拟数据 - 实际项目中应该从API获取
const mockWhitelistData = [
	{
		id: '1',
		pair: 'BTC-USDT',
		exchange: 'OKX',
		spot_symbol: 'BTC-USDT',
		swap_symbol: 'BTC-USDT-SWAP',
		status: 'active',
		funding_rate: '0.0012',
		score: '87',
		last_update: '2023-10-25 08:30:45',
	},
	{
		id: '2',
		pair: 'ETH-USDT',
		exchange: 'OKX',
		spot_symbol: 'ETH-USDT',
		swap_symbol: 'ETH-USDT-SWAP',
		status: 'active',
		funding_rate: '0.0008',
		score: '82',
		last_update: '2023-10-25 08:30:45',
	},
	{
		id: '3',
		pair: 'SOL-USDT',
		exchange: 'OKX',
		spot_symbol: 'SOL-USDT',
		swap_symbol: 'SOL-USDT-SWAP',
		status: 'inactive',
		funding_rate: '0.0015',
		score: '75',
		last_update: '2023-10-25 08:30:45',
	},
	{
		id: '4',
		pair: 'XRP-USDT',
		exchange: 'OKX',
		spot_symbol: 'XRP-USDT',
		swap_symbol: 'XRP-USDT-SWAP',
		status: 'active',
		funding_rate: '0.0010',
		score: '79',
		last_update: '2023-10-25 08:30:45',
	},
];

const FundingRateWhitelistPage = () => {
	const [whitelistData, setWhitelistData] = useState(mockWhitelistData);
	const [isAddModalOpen, setIsAddModalOpen] = useState(false);

	// 处理状态切换
	const handleToggleStatus = (id: string) => {
		setWhitelistData((prev) =>
			prev.map((item) => {
				if (item.id === id) {
					return {
						...item,
						status: item.status === 'active' ? 'inactive' : 'active',
					};
				}
				return item;
			}),
		);
	};

	// 处理编辑操作
	const handleEdit = (id: string) => {
		console.log('编辑交易对:', id);
		// 实现编辑逻辑
	};

	// 处理添加新交易对
	const handleAddPair = () => {
		setIsAddModalOpen(true);
	};

	return (
		<PageWrapper>
			<div className="flex flex-col gap-4">
				<div className="flex justify-between items-center">
					<h1 className="text-2xl font-bold">白名单管理</h1>
					<Button
						variant="solid"
						color="blue"
						icon="HeroPlus"
						onClick={handleAddPair}>
						添加交易对
					</Button>
				</div>

				<Card>
					<CardBody>
						<Table>
							<THead>
								<Tr>
									<Th>交易对</Th>
									<Th>交易所</Th>
									<Th>现货符号</Th>
									<Th>合约符号</Th>
									<Th>资金费率</Th>
									<Th>评分</Th>
									<Th>状态</Th>
									<Th>操作</Th>
								</Tr>
							</THead>
							<TBody>
								{whitelistData.map((item) => (
									<Tr key={item.id}>
										<Td>
											<div className="font-bold">{item.pair}</div>
										</Td>
										<Td>{item.exchange}</Td>
										<Td>{item.spot_symbol}</Td>
										<Td>{item.swap_symbol}</Td>
										<Td className="text-right">{parseFloat(item.funding_rate) * 100}%</Td>
										<Td>{item.score}</Td>
										<Td>
											<Badge
												color={item.status === 'active' ? 'emerald' : 'red'}
												className="text-xs">
												{item.status === 'active' ? '启用' : '禁用'}
											</Badge>
										</Td>
										<Td>
											<div className="flex gap-2">
												<Button
													variant="outline"
													color={item.status === 'active' ? 'red' : 'emerald'}
													size="sm"
													icon={item.status === 'active' ? 'HeroXMark' : 'HeroCheck'}
													onClick={() => handleToggleStatus(item.id)}>
													{item.status === 'active' ? '禁用' : '启用'}
												</Button>
												<Button
													variant="outline"
													color="blue"
													size="sm"
													icon="HeroPencil"
													onClick={() => handleEdit(item.id)}>
													编辑
												</Button>
											</div>
										</Td>
									</Tr>
								))}
							</TBody>
						</Table>
					</CardBody>
				</Card>

				{/* 这里可以添加模态框组件用于添加/编辑交易对 */}
			</div>
		</PageWrapper>
	);
};

export default FundingRateWhitelistPage; 