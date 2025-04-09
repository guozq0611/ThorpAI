import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    // 解析请求体
    const body = await request.json();
    
    // 验证必要参数
    if (!body.symbol || !body.exchange1 || !body.exchange2) {
      return NextResponse.json({ 
        success: false, 
        message: '缺少必要参数: symbol, exchange1, exchange2' 
      }, { status: 400 });
    }

    // 构建请求Python后端的参数
    const pythonApiUrl = process.env.PYTHON_API_URL || 'http://localhost:8000';
    
    // 调用Python后端API
    const response = await fetch(`${pythonApiUrl}/api/strategy/exchange-arbitrage/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json({ 
        success: false, 
        message: `Python后端错误: ${errorData.message || response.statusText}` 
      }, { status: response.status });
    }

    // 返回Python后端的结果
    const result = await response.json();
    return NextResponse.json({ success: true, data: result });
    
  } catch (error) {
    console.error('执行套利API错误:', error);
    return NextResponse.json({ 
      success: false, 
      message: `执行套利失败: ${error instanceof Error ? error.message : '未知错误'}` 
    }, { status: 500 });
  }
} 