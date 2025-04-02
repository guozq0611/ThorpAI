'use client';

import React, { FC, ReactNode } from 'react';
import useMounted from '../hooks/useMounted';

interface IMountedProps {
	children: ReactNode;
	fallback?: ReactNode;
}
const Mounted: FC<IMountedProps> = ({ children, fallback }) => {
	const { mounted } = useMounted();

	if (mounted) return <>{children}</>;
	return fallback || null;
};

export default Mounted;
