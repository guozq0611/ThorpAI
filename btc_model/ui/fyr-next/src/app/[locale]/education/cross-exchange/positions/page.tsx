'use client';

import { Card } from '@/components/ui/Card';
import { Table } from '@/components/ui/Table';
import { useState, useEffect } from 'react';

interface Position {
  id: string;
  symbol: string;
  exchange: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnL: number;
  realizedPnL: number;
  leverage: number;
}

export default function CrossExchangePositionsPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: 从API获取持仓数据
    const fetchPositions = async () => {
      try {
        // const response = await fetch('/api/trading/cross-exchange/positions');
        // const data = await response.json();
        // setPositions(data);
      } catch (error) {
        console.error('Failed to fetch positions:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchPositions();
  }, []);

  const columns = [
    { header: '交易对', accessorKey: 'symbol' },
    { header: '交易所', accessorKey: 'exchange' },
    { header: '方向', accessorKey: 'side' },
    { header: '持仓量', accessorKey: 'size' },
    { header: '开仓价', accessorKey: 'entryPrice' },
    { header: '当前价', accessorKey: 'currentPrice' },
    { header: '未实现盈亏', accessorKey: 'unrealizedPnL' },
    { header: '已实现盈亏', accessorKey: 'realizedPnL' },
    { header: '杠杆', accessorKey: 'leverage' },
  ];

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">跨所套利策略持仓</h1>
      <Card className="p-4">
        <Table
          columns={columns}
          data={positions}
          loading={loading}
        />
      </Card>
    </div>
  );
} 