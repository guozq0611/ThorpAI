'use client';

import { Card } from '@/components/ui/Card';
import { StrategyMonitor } from '@/components/trading/StrategyMonitor';

export default function StrategiesPage() {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">策略监控</h1>
      <Card className="p-4">
        <StrategyMonitor />
      </Card>
    </div>
  );
} 