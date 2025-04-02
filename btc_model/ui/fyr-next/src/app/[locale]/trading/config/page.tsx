'use client';

import { Card } from '@/components/ui/Card';
import { StrategyConfig } from '@/components/trading/StrategyConfig';

export default function ConfigPage() {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">策略配置</h1>
      <Card className="p-4">
        <StrategyConfig />
      </Card>
    </div>
  );
} 