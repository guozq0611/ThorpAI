'use client';

import React, { cloneElement, FC, HTMLAttributes, ReactElement, ReactNode, useState } from 'react';
import classNames from 'classnames';
import { usePopper } from 'react-popper';
import * as PopperJS from '@popperjs/core';
import Icon from '../icon/Icon';
import Portal from '../layouts/Portal/Portal';
import { TBorderWidth } from '../../types/borderWidth.type';
import { TRounded } from '../../types/rounded.type';
import themeConfig from '../../config/theme.config';

const getComponentName = (child: ReactNode): string => {
	// @ts-ignore
	return child?.props['data-component-name'] || child?.type?.displayName || child?.type;
};

interface ITooltipProps extends HTMLAttributes<HTMLDivElement> {
	children?: ReactNode;
	className?: string;
	text: string;
	placement?: PopperJS.Placement;
	borderWidth?: TBorderWidth;
	rounded?: TRounded;
}
const Tooltip: FC<ITooltipProps> = (props) => {
	const {
		children,
		className,
		text,
		placement = 'top',
		borderWidth = 'border',
		rounded = themeConfig.rounded,
		...rest
	} = props;

	const [isOpen, setIsOpen] = useState<boolean>(false);

	const [referenceElement, setReferenceElement] = useState<HTMLElement | null>(null);
	const [popperElement, setPopperElement] = useState<HTMLElement | null>(null);
	const [arrowElement, setArrowElement] = useState<HTMLElement | null>(null);
	const { styles, attributes } = usePopper(referenceElement, popperElement, {
		placement,
		modifiers: [{ name: 'arrow', options: { element: arrowElement } }],
	});

	const REFERENCE_PROPS = {
		onMouseEnter: () => setIsOpen(true),
		onMouseLeave: () => setIsOpen(false),
	};

	return (
		<>
			{['string', 'undefined'].includes(typeof children) ? (
				<span
					data-component-name='Tooltip/Reference'
					ref={setReferenceElement}
					className='cursor-pointer'
					{...REFERENCE_PROPS}>
					{children || (
						<Icon
							icon='HeroInformationCircle'
							className={classNames('inline-flex', className)}
						/>
					)}
				</span>
			) : (
				cloneElement(children as ReactElement, {
					// @ts-ignore
					'data-component-name': `${getComponentName(children)} is cloned with Tooltip`,
					ref: setReferenceElement,
					// @ts-expect-error
					className: classNames('cursor-pointer', children.props.className),
					...REFERENCE_PROPS,
				})
			)}
			{isOpen && text !== '' && (
				<Portal>
					<div
						data-component-name='Tooltip/Popper'
						ref={setPopperElement}
						style={styles.popper}
						className={classNames(
							'z-[9999] m-2 px-2 py-1',
							'max-w-xs',
							'border-zinc-500/10 shadow-lg backdrop-blur-sm',
							[`${borderWidth}`],
							[`${rounded}`],
							className,
						)}
						{...attributes.popper}
						{...rest}>
						{text}
						<div ref={setArrowElement} style={styles.arrow} />
					</div>
				</Portal>
			)}
		</>
	);
};
Tooltip.displayName = 'Tooltip';

export default Tooltip;
