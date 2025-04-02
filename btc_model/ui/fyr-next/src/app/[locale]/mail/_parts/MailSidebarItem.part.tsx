import React, { Dispatch, FC, SetStateAction, useEffect, useMemo, useState } from 'react';
import { Editable, Slate, withReact } from 'slate-react';
import { createEditor } from 'slate';
import classNames from 'classnames';
import { TMail } from '@/types/common/mail.type';
import Icon from '@/components/icon/Icon';

interface MailSidebarItemProps extends TMail {
	active?: number[];
	setActive: Dispatch<SetStateAction<number[]>>;
}
const MailSidebarItemPart: FC<MailSidebarItemProps> = (props) => {
	const { active, setActive, id, user, isNew, fold, dateTime, title, content, attachment, flag } =
		props;

	const isActive = active?.includes(id);

	const [metaKeyStatus, setMetaKeyStatus] = useState<boolean>(false);
	useEffect(() => {
		const handleKeyPress = (event: KeyboardEvent) => {
			if (event.metaKey) {
				setMetaKeyStatus(true);
			}
		};

		document.addEventListener('keydown', handleKeyPress);

		return () => {
			document.removeEventListener('keydown', handleKeyPress);
		};
	}, []);
	useEffect(() => {
		const handleKeyUnPress = (event: KeyboardEvent) => {
			if (!event.metaKey) {
				setMetaKeyStatus(false);
			}
		};

		document.addEventListener('keyup', handleKeyUnPress);

		return () => {
			document.removeEventListener('keyup', handleKeyUnPress);
		};
	}, []);

	const handleClick = () => {
		if (metaKeyStatus) {
			if (typeof active === 'object') {
				const index = active.indexOf(id);

				if (index === -1) {
					active.push(id);
				} else {
					active.splice(index, 1);
				}

				setActive([...active]);
			}
		} else {
			setActive([id]);
		}
	};

	const editor = useMemo(() => withReact(createEditor()), []);

	return (
		<div
			className={classNames('group border-dashed border-b-zinc-500/50', {
				'[&:not(:last-child)]:border-b': !isActive,
				active: isActive,
			})}>
			{}
			<div
				className='flex cursor-pointer gap-2 rounded-lg p-4 ps-0 group-[.active]:bg-blue-500 group-[.active]:text-white'
				onClick={() => handleClick()}>
				<div className='flex-shrink-0'>
					{isNew && <div className='h-full w-2 rounded-full bg-blue-500' />}
				</div>
				<div className='grow'>
					<div className='flex flex-wrap justify-between'>
						<div className='text-xl font-bold'>
							{`${user.firstName} ${user.lastName}`}
						</div>
						<div className='flex gap-2'>
							<div className='text-zinc-500 group-[.active]:text-zinc-100'>
								{fold}
							</div>
							<div className='text-zinc-500 group-[.active]:text-zinc-100'>
								{dateTime}
							</div>
						</div>
					</div>
					<div className='flex flex-wrap justify-between'>
						<div className=''>{title}</div>
						<div className='flex gap-2'>
							{!!attachment && <Icon icon='HeroPaperClip' />}
							{flag && <Icon icon='HeroFlag' color='amber' />}
						</div>
					</div>

					<div className='line-clamp-2 text-zinc-500 group-[.active]:text-white/50'>
						<Slate editor={editor} initialValue={content}>
							<Editable readOnly placeholder='Enter some plain text...' />
						</Slate>
					</div>
				</div>
			</div>
		</div>
	);
};

export default MailSidebarItemPart;
