import React, { FC, ReactNode, useEffect, useState } from 'react';
import classNames from 'classnames';
import { TColors } from '@/types/colors.type';
import { TColorIntensity } from '@/types/colorIntensities.type';
import themeConfig from '@/config/theme.config';

interface TabItemProps {
  id: string;
  title: string;
  children: ReactNode;
  className?: string;
}

export const TabItem: FC<TabItemProps> = ({ children }) => {
  // 这个组件只是一个容器，实际渲染由Tabs组件控制
  return <>{children}</>;
};

interface TabsProps {
  activeTabId?: string;
  onTabChange?: (tabId: string) => void;
  children: ReactNode;
  className?: string;
  color?: TColors;
  colorIntensity?: TColorIntensity;
}

const Tabs: FC<TabsProps> = ({
  activeTabId,
  onTabChange,
  children,
  className,
  color = themeConfig.themeColor,
  colorIntensity = themeConfig.themeColorShade,
}) => {
  const [internalActiveTab, setInternalActiveTab] = useState<string | undefined>(activeTabId);
  
  // 提取TabItem组件
  const tabItems = React.Children.toArray(children).filter(
    (child) => React.isValidElement(child) && child.type === TabItem
  ) as React.ReactElement<TabItemProps>[];
  
  // 如果没有活动标签页，默认选择第一个
  useEffect(() => {
    if (!internalActiveTab && tabItems.length > 0) {
      const firstTabId = tabItems[0].props.id;
      setInternalActiveTab(firstTabId);
      onTabChange?.(firstTabId);
    }
  }, [internalActiveTab, tabItems, onTabChange]);

  // 当外部activeTabId改变时更新内部状态
  useEffect(() => {
    if (activeTabId && activeTabId !== internalActiveTab) {
      setInternalActiveTab(activeTabId);
    }
  }, [activeTabId]);

  // 切换标签页
  const handleTabClick = (tabId: string) => {
    setInternalActiveTab(tabId);
    onTabChange?.(tabId);
  };

  // 活动标签的内容
  const activeTabContent = tabItems.find(
    (tab) => tab.props.id === internalActiveTab
  )?.props.children;

  return (
    <div data-component-name="Tabs" className={classNames('w-full', className)}>
      <div className="border-b border-gray-200 dark:border-gray-700">
        <ul className="flex flex-wrap -mb-px">
          {tabItems.map((tab) => {
            const isActive = tab.props.id === internalActiveTab;
            return (
              <li key={tab.props.id} className="mr-2">
                <button
                  onClick={() => handleTabClick(tab.props.id)}
                  className={classNames(
                    'inline-block py-2 px-4 text-sm font-medium',
                    'rounded-t-lg border-b-2',
                    `${themeConfig.transition}`,
                    isActive
                      ? `border-${color}-${colorIntensity} text-${color}-${colorIntensity}`
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-600 dark:text-gray-400 dark:hover:text-gray-300'
                  )}
                >
                  {tab.props.title}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
      <div className="py-4">{activeTabContent}</div>
    </div>
  );
};

export default Tabs; 