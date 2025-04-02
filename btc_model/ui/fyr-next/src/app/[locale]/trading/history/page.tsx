'use client';

import { Card } from '@/components/ui/Card';
import { OrderHistory } from '@/components/trading/OrderHistory';

export default function HistoryPage() {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">订单历史</h1>
      <Card className="p-4">
        <OrderHistory />
      </Card>
    </div>
  );
} 