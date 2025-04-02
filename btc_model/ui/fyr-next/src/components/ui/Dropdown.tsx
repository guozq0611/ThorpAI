'use client';

import React, {
	cloneElement,
	Dispatch,
	ElementType,
	FC,
	forwardRef,
	HTMLAttributes,
	ReactElement,
	ReactNode,
	SetStateAction,
	useCallback,
	useRef,
	useState,
} from 'react';
import { usePopper } from 'react-popper';
import classNames from 'classnames';
import * as PopperJS from '@popperjs/core';
import { TBorderWidth } from '@/types/borderWidth.type';
import { TRounded } from '@/types/rounded.type';
import { TColors } from '@/types/colors.type';
import { TColorIntensity } from '@/types/colorIntensities.type';
import { TIcons } from '@/types/icons.type';
import { usePathname, useRouter } from 'next/navigation';
import themeConfig from '@/config/theme.config';
import useOnClickOutside from '@/hooks/useOnClickOutside';
import { IButtonProps } from '@/components/ui/Button';
import Icon from '@/components/icon/Icon';

export interface IDropdownProps extends HTMLAttributes<HTMLElement> {
	children: ReactElement<IDropdownToggleProps>[] | ReactElement<IDropdownMenuProps>[];
	className?: string;
	/* If you want to interfere with the open-closed state, you can use it by defining the state. */
	isOpen?: boolean | null;
	setIsOpen?: Dispatch<SetStateAction<boolean>>;
	tag?: ElementType;
}
const Dropdown: FC<IDropdownProps> = (props) => {
	const { children, className, isOpen = null, setIsOpen, tag: Tag = 'div' } = props;

	const [state, setState] = useState<boolean>(
		!!(isOpen !== null && !!setIsOpen ? isOpen : false),
	);

	const dropdownRef = useRef(null);
	const [referenceElement, setReferenceElement] = useState<HTMLElement | null>(null);

	const setRefs = useCallback((node: HTMLElement | null) => {
		// @ts-ignore
		dropdownRef.current = node;
		setReferenceElement(node);
	}, []);

	const classes = classNames('inline-flex');

	// Clicking outside to close
	const closeMenu = useCallback(() => {
		if (isOpen !== null && !!setIsOpen) {
			setIsOpen(false);
		} else {
			setState(false);
		}
	}, [isOpen, setIsOpen]);
	// @ts-ignore
	useOnClickOutside(dropdownRef, closeMenu);

	return (
		<Tag
			data-component-name='Dropdown'
			ref={setRefs}
			className={classNames(classes, className)}>
			{children.map((child: ReactElement, index: number) =>
				// @ts-expect-error
				['DropdownMenu', 'DropdownToggle'].includes(child.type.displayName as string)
					? cloneElement(child, {
							// @ts-ignore
							isOpen: isOpen !== null && !!setIsOpen ? isOpen : state,
							setIsOpen: isOpen !== null && !!setIsOpen ? setIsOpen : setState,
							referenceElement: referenceElement,
							setReferenceElement: setReferenceElement,
							key: index,
						})
					: child,
			)}
		</Tag>
	);
};
Dropdown.displayName = 'Dropdown';

interface IDropdownToggleProps {
	children: ReactElement<IButtonProps | IDropdownItemProps>;
	hasIcon?: boolean;
	isOpen?: boolean;
	setIsOpen?: Dispatch<SetStateAction<boolean>>;
	setReferenceElement?: Dispatch<SetStateAction<HTMLElement>>;
}
export const DropdownToggle: FC<IDropdownToggleProps> = (props) => {
	const { children, isOpen = false, setIsOpen, hasIcon = true, setReferenceElement } = props;

	return cloneElement(children, {
		// @ts-expect-error
		'data-component-name': `Dropdown/DropdownToggle [${children.type.displayName}]`,
		ref: setReferenceElement,
		onClick: () => {
			// @ts-expect-error
			// eslint-disable-next-line @typescript-eslint/no-unused-expressions
			children?.props?.onClick ? children.props.onClick() : null;
			if (setIsOpen) {
				setIsOpen(!isOpen);
			}
		},
		rightIcon: hasIcon
			? // @ts-expect-error
				(children.type.displayName === 'Button' && 'HeroChevronDown') || 'HeroChevronRight'
			: undefined,
		isActive: isOpen,
		className: classNames(
			{
				// Only presentation
				show: isOpen,
			},
			children?.props?.className,
		),
		'aria-expanded': isOpen,
	});
};
DropdownToggle.displayName = 'DropdownToggle';

interface IDropdownMenuProps extends HTMLAttributes<HTMLUListElement> {
	borderWidth?: TBorderWidth;
	children: ReactNode | ReactNode[];
	className?: string;
	fallbackPlacements?: PopperJS.Placement[];
	isCloseAfterLeave?: boolean;
	isOpen?: boolean;
	placement?: PopperJS.Placement;
	rounded?: TRounded;
	setIsOpen?: Dispatch<SetStateAction<boolean>>;
	referenceElement?: HTMLElement;
}
export const DropdownMenu: FC<IDropdownMenuProps> = (props) => {
	const {
		isOpen = false,
		setIsOpen,
		children,
		className,
		placement = 'bottom-start',
		isCloseAfterLeave = true,
		borderWidth = themeConfig.borderWidth,
		rounded = themeConfig.rounded,
		fallbackPlacements = [`top-start`, `bottom-start`],
		referenceElement,
		...rest
	} = props;

	const [popperElement, setPopperElement] = useState<HTMLElement | null>(null);
	const { styles, attributes } = usePopper(referenceElement, popperElement, {
		placement,
		modifiers: [
			{
				name: 'flip',
				options: {
					fallbackPlacements: fallbackPlacements,
				},
			},
		],
	});

	const onMouseLeave = isCloseAfterLeave && setIsOpen ? () => setIsOpen(false) : undefined;

	if (isOpen) {
		return (
			<ul
				data-component-name='Dropdown/DropdownMenu'
				role='presentation'
				ref={setPopperElement}
				// dynamic positioning must be disabled for responsive alignment
				style={styles.popper}
				data-placement={placement}
				className={classNames(
					'py-2',
					'z-[9999]',
					'border-zinc-300/25 bg-white shadow-lg dark:border-zinc-800/50 dark:bg-zinc-900',
					[`${borderWidth}`, `${rounded}`],
					className,
				)}
				onMouseLeave={onMouseLeave}
				{...attributes.popper}
				{...rest}>
				{children}
			</ul>
		);
	}
	return null;
};
DropdownMenu.displayName = 'DropdownMenu';

interface IDropdownItemProps extends HTMLAttributes<HTMLLIElement> {
	children: ReactNode;
	className?: string;
	color?: TColors;
	colorIntensity?: TColorIntensity;
	isActive?: boolean;
	icon?: TIcons;
	rightIcon?: TIcons;
}
export const DropdownItem = forwardRef<HTMLLIElement, IDropdownItemProps>((props, ref) => {
	const {
		children,

		className,

		color = themeConfig.themeColor,

		colorIntensity = themeConfig.themeColorShade,

		isActive = false,

		icon,

		rightIcon,
		...rest
	} = props;
	const classes = classNames(
		'px-4 py-2',
		'flex items-center',
		'whitespace-nowrap',
		'cursor-pointer',
		'border-zinc-300/25 dark:border-zinc-800/50',
		{
			[`text-${color}-${colorIntensity}`]: isActive,
			'text-zinc-500 hover:text-zinc-950 dark:hover:text-zinc-100': !isActive,
		},
		themeConfig.transition,
	);
	return (
		<li
			data-component-name='Dropdown/DropdownItem'
			ref={ref}
			className={classNames(classes, className)}
			{...rest}>
			{icon && <Icon icon={icon} className='inline-flex text-xl ltr:mr-1.5 rtl:ml-1.5' />}
			{children}
			{rightIcon && (
				<Icon icon={rightIcon} className='inline-flex text-xl ltr:ml-1.5 rtl:mr-1.5' />
			)}
		</li>
	);
});
DropdownItem.displayName = 'DropdownItem';

interface IDropdownNavLinkItemProps extends IDropdownItemProps {
	to: string;
}
export const DropdownNavLinkItem: FC<IDropdownNavLinkItemProps> = (props) => {
	const { to, children, ...rest } = props;

	const router = useRouter();
	const pathname = usePathname();
	const match = pathname === to;

	return (
		<DropdownItem {...rest} onClick={() => router.push(to)} isActive={match}>
			{children}
		</DropdownItem>
	);
};

export default Dropdown;
