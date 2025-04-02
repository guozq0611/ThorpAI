// @ts-nocheck

import { Editor, Element as SlateElement, Transforms } from 'slate';
import { useSlate } from 'slate-react';
import React, { FC, ReactNode } from 'react';
import classNames from 'classnames';
import Button from '../ui/Button';

const LIST_TYPES = ['numbered-list', 'bulleted-list'];
const TEXT_ALIGN_TYPES = ['left', 'center', 'right', 'justify'];

const isBlockActive = (editor, format, blockType = 'type') => {
	const { selection } = editor;
	if (!selection) return false;

	const [match] = Array.from(
		Editor.nodes(editor, {
			at: Editor.unhangRange(editor, selection),
			match: (n) =>
				!Editor.isEditor(n) && SlateElement.isElement(n) && n[blockType] === format,
		}),
	);

	return !!match;
};
export const toggleBlock = (editor, format) => {
	const isActive = isBlockActive(
		editor,
		format,

		TEXT_ALIGN_TYPES.includes(format) ? 'align' : 'type',
	);

	const isList = LIST_TYPES.includes(format);

	Transforms.unwrapNodes(editor, {
		match: (n) =>
			!Editor.isEditor(n) &&
			SlateElement.isElement(n) &&
			LIST_TYPES.includes(n.type) &&
			!TEXT_ALIGN_TYPES.includes(format),
		split: true,
	});
	let newProperties: Partial<SlateElement>;

	if (TEXT_ALIGN_TYPES.includes(format)) {
		newProperties = {
			align: isActive ? undefined : format,
		};
	} else {
		newProperties = {
			type: isActive ? 'paragraph' : isList ? 'list-item' : format,
		};
	}

	Transforms.setNodes<SlateElement>(editor, newProperties);

	if (!isActive && isList) {
		const block = { type: format, children: [] };

		Transforms.wrapNodes(editor, block);
	}
};

const isMarkActive = (editor, format) => {
	const marks = Editor.marks(editor);

	return marks ? marks[format] === true : false;
};
export const toggleMark = (editor, format) => {
	const isActive = isMarkActive(editor, format);

	if (isActive) {
		Editor.removeMark(editor, format);
	} else {
		Editor.addMark(editor, format, true);
	}
};

// eslint-disable-next-line react/prop-types
export const Element = ({ attributes, children, element }) => {
	// eslint-disable-next-line react/prop-types
	const style = { textAlign: element.align };
	// eslint-disable-next-line react/prop-types
	switch (element.type) {
		case 'block-quote':
			return (
				<blockquote style={style} {...attributes}>
					{children}
				</blockquote>
			);
		case 'bulleted-list':
			return (
				<ul style={style} {...attributes}>
					{children}
				</ul>
			);
		case 'heading-one':
			return (
				<h1 style={style} {...attributes}>
					{children}
				</h1>
			);
		case 'heading-two':
			return (
				<h2 style={style} {...attributes}>
					{children}
				</h2>
			);
		case 'list-item':
			return (
				<li style={style} {...attributes}>
					{children}
				</li>
			);
		case 'numbered-list':
			return (
				<ol style={style} {...attributes}>
					{children}
				</ol>
			);
		default:
			return (
				<p style={style} {...attributes}>
					{children}
				</p>
			);
	}
};

// eslint-disable-next-line react/prop-types
export const Leaf = ({ attributes, children, leaf }) => {
	// eslint-disable-next-line react/prop-types
	if (leaf.bold) {
		children = <strong>{children}</strong>;
	}

	// eslint-disable-next-line react/prop-types
	if (leaf.code) {
		children = <code>{children}</code>;
	}

	// eslint-disable-next-line react/prop-types
	if (leaf.italic) {
		children = <em>{children}</em>;
	}

	// eslint-disable-next-line react/prop-types
	if (leaf.underline) {
		children = <u>{children}</u>;
	}

	return <span {...attributes}>{children}</span>;
};

// eslint-disable-next-line react/prop-types
export const BlockButton = ({ format, icon }) => {
	const editor = useSlate();
	return (
		<Button
			icon={icon}
			isActive={isBlockActive(
				editor,
				format,

				TEXT_ALIGN_TYPES.includes(format) ? 'align' : 'type',
			)}
			onMouseDown={(event) => {
				event.preventDefault();
				toggleBlock(editor, format);
			}}
		/>
	);
};

// eslint-disable-next-line react/prop-types
export const MarkButton = ({ format, icon }) => {
	const editor = useSlate();
	return (
		<Button
			icon={icon}
			isActive={isMarkActive(editor, format)}
			onMouseDown={(event) => {
				event.preventDefault();
				toggleMark(editor, format);
			}}
		/>
	);
};

// eslint-disable-next-line react/prop-types
export const Toolbar = ({ children }) => {
	return (
		<span className='flex items-center justify-between bg-zinc-100 dark:bg-zinc-800'>
			{children}
		</span>
	);
};

interface IToolbarChildProps {
	children: ReactNode;
	className?: string;
}
export const ToolbarChild: FC<IToolbarChildProps> = ({ children, className }) => {
	return <span className={classNames('flex items-center', className)}>{children}</span>;
};
