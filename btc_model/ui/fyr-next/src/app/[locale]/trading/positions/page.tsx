'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { PositionMonitor } from '@/components/trading/PositionMonitor';

export default function PositionsPage() {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">仓位监控</h1>
      <Card className="p-4">
        <PositionMonitor />
      </Card>
    </div>
  );
} 