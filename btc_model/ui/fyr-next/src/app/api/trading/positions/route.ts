import { NextResponse } from 'next/server';
import { MarketDataService } from '@/lib/services/market_data_service';

export async function GET() {
  try {
    const marketDataService = MarketDataService.getInstance();
    const positions = await marketDataService.getPositions();
    return NextResponse.json(positions);
  } catch (error) {
    console.error('Failed to fetch positions:', error);
    return NextResponse.json(
      { error: 'Failed to fetch positions' },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const marketDataService = MarketDataService.getInstance();
    const position = await marketDataService.openPosition(body);
    return NextResponse.json(position);
  } catch (error) {
    console.error('Failed to open position:', error);
    return NextResponse.json(
      { error: 'Failed to open position' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');
    if (!id) {
      return NextResponse.json(
        { error: 'Position ID is required' },
        { status: 400 }
      );
    }

    const marketDataService = MarketDataService.getInstance();
    await marketDataService.closePosition(id);
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Failed to close position:', error);
    return NextResponse.json(
      { error: 'Failed to close position' },
      { status: 500 }
    );
  }
} 