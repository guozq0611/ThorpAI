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
import { RefreshCw, Play, Pause } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface Strategy {
  id: string;
  name: string;
  status: 'running' | 'paused' | 'stopped';
  symbol: string;
  type: string;
  parameters: Record<string, any>;
  performance: {
    totalTrades: number;
    winRate: number;
    profitLoss: number;
    profitLossPercentage: number;
  };
}

export function StrategyMonitor() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchStrategies = async () => {
    setLoading(true);
    try {
      // TODO: 实现与后端的API调用
      const response = await fetch('/api/trading/strategies');
      const data = await response.json();
      setStrategies(data);
    } catch (error) {
      console.error('Failed to fetch strategies:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleStrategy = async (strategyId: string, action: 'start' | 'stop' | 'pause') => {
    try {
      // TODO: 实现与后端的API调用
      await fetch(`/api/trading/strategies/${strategyId}/${action}`, {
        method: 'POST',
      });
      fetchStrategies();
    } catch (error) {
      console.error(`Failed to ${action} strategy:`, error);
    }
  };

  useEffect(() => {
    fetchStrategies();
    const interval = setInterval(fetchStrategies, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">策略监控</h2>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchStrategies}
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>策略名称</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>交易对</TableHead>
            <TableHead>类型</TableHead>
            <TableHead>总交易次数</TableHead>
            <TableHead>胜率</TableHead>
            <TableHead>盈亏</TableHead>
            <TableHead>操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {strategies.map((strategy) => (
            <TableRow key={strategy.id}>
              <TableCell>{strategy.name}</TableCell>
              <TableCell>
                <Badge
                  variant={
                    strategy.status === 'running'
                      ? 'success'
                      : strategy.status === 'paused'
                      ? 'warning'
                      : 'destructive'
                  }
                >
                  {strategy.status === 'running'
                    ? '运行中'
                    : strategy.status === 'paused'
                    ? '已暂停'
                    : '已停止'}
                </Badge>
              </TableCell>
              <TableCell>{strategy.symbol}</TableCell>
              <TableCell>{strategy.type}</TableCell>
              <TableCell>{strategy.performance.totalTrades}</TableCell>
              <TableCell>{strategy.performance.winRate.toFixed(2)}%</TableCell>
              <TableCell>
                <span
                  className={
                    strategy.performance.profitLoss >= 0
                      ? 'text-green-500'
                      : 'text-red-500'
                  }
                >
                  {strategy.performance.profitLoss.toFixed(2)} (
                  {strategy.performance.profitLossPercentage.toFixed(2)}%)
                </span>
              </TableCell>
              <TableCell>
                <div className="flex space-x-2">
                  {strategy.status === 'stopped' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleStrategy(strategy.id, 'start')}
                    >
                      <Play className="h-4 w-4" />
                    </Button>
                  )}
                  {strategy.status === 'running' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleStrategy(strategy.id, 'pause')}
                    >
                      <Pause className="h-4 w-4" />
                    </Button>
                  )}
                  {strategy.status === 'paused' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleStrategy(strategy.id, 'start')}
                    >
                      <Play className="h-4 w-4" />
                    </Button>
                  )}
                  {(strategy.status === 'running' ||
                    strategy.status === 'paused') && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleStrategy(strategy.id, 'stop')}
                    >
                      停止
                    </Button>
                  )}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
} 