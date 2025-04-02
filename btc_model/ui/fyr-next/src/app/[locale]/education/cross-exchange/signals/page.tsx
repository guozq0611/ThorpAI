'use client';

import { Card } from '@/components/ui/Card';
import { Table } from '@/components/ui/Table';
import { useState, useEffect } from 'react';

interface Signal {
  id: string;
  timestamp: string;
  symbol: string;
  exchange1: string;
  exchange2: string;
  price1: number;
  price2: number;
  spread: number;
  status: 'active' | 'executed' | 'cancelled';
}

export default function CrossExchangeSignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: 从API获取交易信号数据
    const fetchSignals = async () => {
      try {
        // const response = await fetch('/api/trading/cross-exchange/signals');
        // const data = await response.json();
        // setSignals(data);
      } catch (error) {
        console.error('Failed to fetch signals:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSignals();
  }, []);

  const columns = [
    { header: '时间', accessorKey: 'timestamp' },
    { header: '交易对', accessorKey: 'symbol' },
    { header: '交易所1', accessorKey: 'exchange1' },
    { header: '交易所2', accessorKey: 'exchange2' },
    { header: '价格1', accessorKey: 'price1' },
    { header: '价格2', accessorKey: 'price2' },
    { header: '价差', accessorKey: 'spread' },
    { header: '状态', accessorKey: 'status' },
  ];

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">跨所套利交易信号</h1>
      <Card className="p-4">
        <Table
          columns={columns}
          data={signals}
          loading={loading}
        />
      </Card>
    </div>
  );
} 