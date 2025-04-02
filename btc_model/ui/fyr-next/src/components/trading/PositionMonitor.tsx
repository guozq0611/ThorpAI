'use client';

import { useEffect, useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';

interface Position {
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercentage: number;
  leverage: number;
}

export function PositionMonitor() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchPositions = async () => {
    setLoading(true);
    try {
      // TODO: 实现与后端的API调用
      const response = await fetch('/api/trading/positions');
      const data = await response.json();
      setPositions(data);
    } catch (error) {
      console.error('Failed to fetch positions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPositions();
    // 设置定时刷新
    const interval = setInterval(fetchPositions, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">当前仓位</h2>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchPositions}
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>交易对</TableHead>
            <TableHead>方向</TableHead>
            <TableHead>数量</TableHead>
            <TableHead>入场价格</TableHead>
            <TableHead>当前价格</TableHead>
            <TableHead>未实现盈亏</TableHead>
            <TableHead>杠杆</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {positions.map((position) => (
            <TableRow key={position.symbol}>
              <TableCell>{position.symbol}</TableCell>
              <TableCell>
                <span className={position.side === 'long' ? 'text-green-500' : 'text-red-500'}>
                  {position.side === 'long' ? '多' : '空'}
                </span>
              </TableCell>
              <TableCell>{position.size}</TableCell>
              <TableCell>{position.entryPrice}</TableCell>
              <TableCell>{position.currentPrice}</TableCell>
              <TableCell>
                <span className={position.pnl >= 0 ? 'text-green-500' : 'text-red-500'}>
                  {position.pnl.toFixed(2)} ({position.pnlPercentage.toFixed(2)}%)
                </span>
              </TableCell>
              <TableCell>{position.leverage}x</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
} 