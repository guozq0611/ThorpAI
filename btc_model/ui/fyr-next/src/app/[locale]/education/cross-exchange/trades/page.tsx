'use client';

import { Card } from '@/components/ui/Card';
import { Table } from '@/components/ui/Table';
import { useState, useEffect } from 'react';

interface Trade {
  id: string;
  timestamp: string;
  symbol: string;
  exchange: string;
  side: 'buy' | 'sell';
  price: number;
  amount: number;
  fee: number;
  pnl: number;
}

export default function CrossExchangeTradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: 从API获取成交订单数据
    const fetchTrades = async () => {
      try {
        // const response = await fetch('/api/trading/cross-exchange/trades');
        // const data = await response.json();
        // setTrades(data);
      } catch (error) {
        console.error('Failed to fetch trades:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTrades();
  }, []);

  const columns = [
    { header: '时间', accessorKey: 'timestamp' },
    { header: '交易对', accessorKey: 'symbol' },
    { header: '交易所', accessorKey: 'exchange' },
    { header: '方向', accessorKey: 'side' },
    { header: '价格', accessorKey: 'price' },
    { header: '数量', accessorKey: 'amount' },
    { header: '手续费', accessorKey: 'fee' },
    { header: '盈亏', accessorKey: 'pnl' },
  ];

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">跨所套利成交订单</h1>
      <Card className="p-4">
        <Table
          columns={columns}
          data={trades}
          loading={loading}
        />
      </Card>
    </div>
  );
} 