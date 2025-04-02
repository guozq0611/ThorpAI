import { NextResponse } from 'next/server';
import { MarketDataService } from '@/lib/services/market_data_service';

export async function GET() {
  try {
    const marketDataService = MarketDataService.getInstance();
    const strategies = await marketDataService.getStrategies();
    return NextResponse.json(strategies);
  } catch (error) {
    console.error('Failed to fetch strategies:', error);
    return NextResponse.json(
      { error: 'Failed to fetch strategies' },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const marketDataService = MarketDataService.getInstance();
    const strategy = await marketDataService.saveStrategy(body);
    return NextResponse.json(strategy);
  } catch (error) {
    console.error('Failed to save strategy:', error);
    return NextResponse.json(
      { error: 'Failed to save strategy' },
      { status: 500 }
    );
  }
}

export async function PUT(request: Request) {
  try {
    const body = await request.json();
    const marketDataService = MarketDataService.getInstance();
    const strategy = await marketDataService.updateStrategy(body);
    return NextResponse.json(strategy);
  } catch (error) {
    console.error('Failed to update strategy:', error);
    return NextResponse.json(
      { error: 'Failed to update strategy' },
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
        { error: 'Strategy ID is required' },
        { status: 400 }
      );
    }

    const marketDataService = MarketDataService.getInstance();
    await marketDataService.deleteStrategy(id);
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Failed to delete strategy:', error);
    return NextResponse.json(
      { error: 'Failed to delete strategy' },
      { status: 500 }
    );
  }
} 