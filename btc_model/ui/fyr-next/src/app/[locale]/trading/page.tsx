'use client';

import { Card } from '@/components/ui/Card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PositionMonitor } from '@/components/trading/PositionMonitor';
import { StrategyMonitor } from '@/components/trading/StrategyMonitor';
import { TradeExecution } from '@/components/trading/TradeExecution';
import { OrderHistory } from '@/components/trading/OrderHistory';
import { StrategyConfig } from '@/components/trading/StrategyConfig';

export default function TradingPage() {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">交易管理系统</h1>
      
      <Tabs defaultValue="positions" className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="positions">仓位监控</TabsTrigger>
          <TabsTrigger value="strategies">策略监控</TabsTrigger>
          <TabsTrigger value="execution">交易执行</TabsTrigger>
          <TabsTrigger value="history">订单历史</TabsTrigger>
          <TabsTrigger value="config">策略配置</TabsTrigger>
        </TabsList>
        
        <TabsContent value="positions">
          <Card className="p-4">
            <PositionMonitor />
          </Card>
        </TabsContent>
        
        <TabsContent value="strategies">
          <Card className="p-4">
            <StrategyMonitor />
          </Card>
        </TabsContent>
        
        <TabsContent value="execution">
          <Card className="p-4">
            <TradeExecution />
          </Card>
        </TabsContent>

        <TabsContent value="history">
          <Card className="p-4">
            <OrderHistory />
          </Card>
        </TabsContent>

        <TabsContent value="config">
          <Card className="p-4">
            <StrategyConfig />
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
} 