import React, { FC, ReactNode } from 'react';

interface IVisibleProps {
	children: ReactNode;
	is: boolean;
}
const Visible: FC<IVisibleProps> = (props) => {
	const { children, is } = props;

	if (is) return <>{children}</>;
	return null;
};

export default Visible;
