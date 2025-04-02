'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import * as z from 'zod';
import { toast } from '@/components/ui/use-toast';
import { Switch } from '@/components/ui/switch';

const formSchema = z.object({
  name: z.string().min(1, '请输入策略名称'),
  type: z.enum(['grid', 'martingale', 'dca', 'custom'], {
    required_error: '请选择策略类型',
  }),
  symbol: z.string().min(1, '请选择交易对'),
  parameters: z.object({
    // 网格策略参数
    gridLevels: z.number().optional(),
    gridSpacing: z.number().optional(),
    gridQuantity: z.number().optional(),
    // 马丁格尔策略参数
    martingaleMultiplier: z.number().optional(),
    martingaleMaxLevels: z.number().optional(),
    martingaleBaseQuantity: z.number().optional(),
    // DCA策略参数
    dcaInterval: z.number().optional(),
    dcaQuantity: z.number().optional(),
    dcaMaxOrders: z.number().optional(),
    // 通用参数
    stopLoss: z.number().optional(),
    takeProfit: z.number().optional(),
    maxPosition: z.number().optional(),
    leverage: z.number().optional(),
  }),
  enabled: z.boolean().default(false),
});

type FormValues = z.infer<typeof formSchema>;

export function StrategyConfig() {
  const [loading, setLoading] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: '',
      type: 'grid',
      symbol: '',
      parameters: {
        gridLevels: 5,
        gridSpacing: 0.02,
        gridQuantity: 0.01,
        martingaleMultiplier: 2,
        martingaleMaxLevels: 5,
        martingaleBaseQuantity: 0.01,
        dcaInterval: 3600,
        dcaQuantity: 0.01,
        dcaMaxOrders: 10,
        stopLoss: 0.05,
        takeProfit: 0.1,
        maxPosition: 1,
        leverage: 1,
      },
      enabled: false,
    },
  });

  const onSubmit = async (values: FormValues) => {
    setLoading(true);
    try {
      // TODO: 实现与后端的API调用
      const response = await fetch('/api/trading/strategies', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(values),
      });

      if (!response.ok) {
        throw new Error('保存策略失败');
      }

      toast({
        title: '保存成功',
        description: '策略配置已更新',
      });

      form.reset();
    } catch (error) {
      console.error('Failed to save strategy:', error);
      toast({
        title: '保存失败',
        description: error instanceof Error ? error.message : '未知错误',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const strategyType = form.watch('type');

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>策略配置</CardTitle>
          <CardDescription>
            配置交易策略参数，支持网格、马丁格尔、DCA等策略
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>策略名称</FormLabel>
                    <FormControl>
                      <Input placeholder="输入策略名称" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>策略类型</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      defaultValue={field.value}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="选择策略类型" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="grid">网格策略</SelectItem>
                        <SelectItem value="martingale">马丁格尔策略</SelectItem>
                        <SelectItem value="dca">DCA策略</SelectItem>
                        <SelectItem value="custom">自定义策略</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="symbol"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>交易对</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      defaultValue={field.value}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="选择交易对" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="BTC/USDT">BTC/USDT</SelectItem>
                        <SelectItem value="ETH/USDT">ETH/USDT</SelectItem>
                        <SelectItem value="SOL/USDT">SOL/USDT</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {strategyType === 'grid' && (
                <>
                  <FormField
                    control={form.control}
                    name="parameters.gridLevels"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>网格层数</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min="1"
                            max="100"
                            {...field}
                            onChange={(e) =>
                              field.onChange(Number(e.target.value))
                            }
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="parameters.gridSpacing"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>网格间距 (%)</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            step="0.01"
                            min="0.01"
                            {...field}
                            onChange={(e) =>
                              field.onChange(Number(e.target.value))
                            }
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="parameters.gridQuantity"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>每格数量</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            step="0.00000001"
                            {...field}
                            onChange={(e) =>
                              field.onChange(Number(e.target.value))
                            }
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </>
              )}

              {strategyType === 'martingale' && (
                <>
                  <FormField
                    control={form.control}
                    name="parameters.martingaleMultiplier"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>倍数</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            step="0.1"
                            min="1"
                            {...field}
                            onChange={(e) =>
                              field.onChange(Number(e.target.value))
                            }
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="parameters.martingaleMaxLevels"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>最大层数</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min="1"
                            max="10"
                            {...field}
                            onChange={(e) =>
                              field.onChange(Number(e.target.value))
                            }
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="parameters.martingaleBaseQuantity"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>基础数量</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            step="0.00000001"
                            {...field}
                            onChange={(e) =>
                              field.onChange(Number(e.target.value))
                            }
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </>
              )}

              {strategyType === 'dca' && (
                <>
                  <FormField
                    control={form.control}
                    name="parameters.dcaInterval"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>定投间隔 (秒)</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min="60"
                            {...field}
                            onChange={(e) =>
                              field.onChange(Number(e.target.value))
                            }
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="parameters.dcaQuantity"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>每次数量</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            step="0.00000001"
                            {...field}
                            onChange={(e) =>
                              field.onChange(Number(e.target.value))
                            }
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="parameters.dcaMaxOrders"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>最大订单数</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min="1"
                            {...field}
                            onChange={(e) =>
                              field.onChange(Number(e.target.value))
                            }
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </>
              )}

              <div className="space-y-4">
                <h3 className="text-lg font-medium">通用参数</h3>
                <FormField
                  control={form.control}
                  name="parameters.stopLoss"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>止损比例 (%)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          {...field}
                          onChange={(e) =>
                            field.onChange(Number(e.target.value))
                          }
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="parameters.takeProfit"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>止盈比例 (%)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          {...field}
                          onChange={(e) =>
                            field.onChange(Number(e.target.value))
                          }
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="parameters.maxPosition"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>最大持仓</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="0"
                          {...field}
                          onChange={(e) =>
                            field.onChange(Number(e.target.value))
                          }
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="parameters.leverage"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>杠杆倍数</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="1"
                          max="125"
                          {...field}
                          onChange={(e) =>
                            field.onChange(Number(e.target.value))
                          }
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="enabled"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">启用策略</FormLabel>
                    </div>
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? '保存中...' : '保存策略'}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
} 