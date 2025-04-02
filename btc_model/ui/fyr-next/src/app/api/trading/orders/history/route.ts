import { NextResponse } from 'next/server';
import { MarketDataService } from '@/lib/services/market_data_service';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const symbol = searchParams.get('symbol');
    const startDate = searchParams.get('startDate');
    const endDate = searchParams.get('endDate');

    const marketDataService = MarketDataService.getInstance();
    const orders = await marketDataService.getOrderHistory({
      symbol,
      startDate: startDate ? new Date(startDate) : undefined,
      endDate: endDate ? new Date(endDate) : undefined,
    });

    return NextResponse.json(orders);
  } catch (error) {
    console.error('Failed to fetch order history:', error);
    return NextResponse.json(
      { error: 'Failed to fetch order history' },
      { status: 500 }
    );
  }
} 