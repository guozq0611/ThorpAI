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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { DatePicker } from '@/components/ui/date-picker';

interface Order {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  type: 'market' | 'limit';
  price: number;
  amount: number;
  status: 'filled' | 'cancelled' | 'rejected';
  filledAmount: number;
  averagePrice: number;
  pnl: number;
  timestamp: string;
}

export function OrderHistory() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [symbol, setSymbol] = useState<string>('');
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      // TODO: 实现与后端的API调用
      const response = await fetch('/api/trading/orders/history');
      const data = await response.json();
      setOrders(data);
    } catch (error) {
      console.error('Failed to fetch orders:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [symbol, startDate, endDate]);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">订单历史</h2>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchOrders}
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      <div className="flex gap-4 mb-4">
        <Select value={symbol} onValueChange={setSymbol}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="选择交易对" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部</SelectItem>
            <SelectItem value="BTC/USDT">BTC/USDT</SelectItem>
            <SelectItem value="ETH/USDT">ETH/USDT</SelectItem>
            <SelectItem value="SOL/USDT">SOL/USDT</SelectItem>
          </SelectContent>
        </Select>

        <DatePicker
          value={startDate}
          onChange={setStartDate}
          placeholder="开始日期"
        />
        <DatePicker
          value={endDate}
          onChange={setEndDate}
          placeholder="结束日期"
        />
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>订单ID</TableHead>
            <TableHead>交易对</TableHead>
            <TableHead>方向</TableHead>
            <TableHead>类型</TableHead>
            <TableHead>价格</TableHead>
            <TableHead>数量</TableHead>
            <TableHead>已成交</TableHead>
            <TableHead>均价</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>盈亏</TableHead>
            <TableHead>时间</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {orders.map((order) => (
            <TableRow key={order.id}>
              <TableCell>{order.id}</TableCell>
              <TableCell>{order.symbol}</TableCell>
              <TableCell>
                <span className={order.side === 'buy' ? 'text-green-500' : 'text-red-500'}>
                  {order.side === 'buy' ? '买入' : '卖出'}
                </span>
              </TableCell>
              <TableCell>{order.type === 'market' ? '市价' : '限价'}</TableCell>
              <TableCell>{order.price}</TableCell>
              <TableCell>{order.amount}</TableCell>
              <TableCell>{order.filledAmount}</TableCell>
              <TableCell>{order.averagePrice}</TableCell>
              <TableCell>
                <span
                  className={
                    order.status === 'filled'
                      ? 'text-green-500'
                      : order.status === 'cancelled'
                      ? 'text-yellow-500'
                      : 'text-red-500'
                  }
                >
                  {order.status === 'filled'
                    ? '已成交'
                    : order.status === 'cancelled'
                    ? '已取消'
                    : '已拒绝'}
                </span>
              </TableCell>
              <TableCell>
                <span className={order.pnl >= 0 ? 'text-green-500' : 'text-red-500'}>
                  {order.pnl.toFixed(2)}
                </span>
              </TableCell>
              <TableCell>{new Date(order.timestamp).toLocaleString()}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
} 