'use client';

import { Card } from '@/components/ui/Card';
import { TradeExecution } from '@/components/trading/TradeExecution';

export default function ExecutionPage() {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">交易执行</h1>
      <Card className="p-4">
        <TradeExecution />
      </Card>
    </div>
  );
} 