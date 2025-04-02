'use client';

import React, { useState } from 'react';
import { TMail } from '@/types/common/mail.type';
import { useRouter } from 'next/navigation';
import PageWrapper from '@/components/layouts/PageWrapper/PageWrapper';
import Subheader, {
	SubheaderLeft,
	SubheaderRight,
	SubheaderSeparator,
} from '@/components/layouts/Subheader/Subheader';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import { appPages } from '@/config/pages.config';
import Container from '@/components/layouts/Container/Container';
import Card, { CardBody, CardFooter, CardFooterChild } from '@/components/ui/Card';
import MailSidebarItemPart from '@/app/[locale]/mail/_parts/MailSidebarItem.part';
import Avatar from '@/components/Avatar';
import MailContentViewerPart from '@/app/[locale]/mail/_parts/MailContentViewer.part';

const mails: TMail[] = [];

const MailJunkClient = () => {
	const [activeItem, setActiveItem] = useState<number[]>([mails[0]?.id]);

	const activeMails = mails.filter((mail) => activeItem.includes(mail.id));

	const router = useRouter();

	return (
		<PageWrapper>
			<Subheader>
				<SubheaderLeft>
					<span>Inbox</span>
					<Badge
						color='blue'
						variant='outline'
						rounded='rounded-full'
						className='border-transparent'>
						{mails.length} mails
					</Badge>
					<Button icon='HeroArrowPath' title='Refresh' />
					<SubheaderSeparator />
					<Button icon='HeroArchiveBox' title='Archive selected mails' />
					<Button icon='HeroTrash' title='Delete selected mails' />
					<Button icon='HeroArchiveBoxXMark' title='Move selected mails to spam' />
					<SubheaderSeparator />
					<Button icon='HeroArrowUturnLeft' title='Reply' />
					<Button icon='HeroArrowUturnRight' title='Forward' />
					<SubheaderSeparator />
					<Button icon='HeroFlag' title='Flag' />
					<SubheaderSeparator />
					<Button icon='HeroBellSlash' title='New Mail' />
				</SubheaderLeft>
				<SubheaderRight>
					<Button
						icon='HeroPencilSquare'
						title='New Mail'
						variant='solid'
						onClick={() => {
							router.push(`../${appPages.mailAppPages.subPages.newMailPages.to}`);
						}}>
						New Mail
					</Button>
				</SubheaderRight>
			</Subheader>
			<Container className='flex shrink-0 grow basis-auto flex-col gap-4 pb-0'>
				<div className='flex h-full flex-wrap content-start'>
					<div className='mb-4 grid h-full w-full grid-cols-12 gap-4'>
						<div className='col-span-12 flex h-full flex-col gap-4 xl:col-span-3'>
							<Card className='h-full'>
								<CardBody className='h-96 overflow-scroll'>
									{mails.map((item) => (
										<MailSidebarItemPart
											key={item.id}
											active={activeItem}
											setActive={setActiveItem}
											// eslint-disable-next-line react/jsx-props-no-spreading
											{...item}
										/>
									))}
								</CardBody>
							</Card>
						</div>
						<div className='col-span-12 flex h-full flex-col gap-4 xl:col-span-9'>
							<Card className='h-full'>
								{activeMails.length === 1 && (
									<CardBody>
										<div className='flex flex-col gap-2'>
											<div className='flex justify-between border-b-[1px] border-dashed border-zinc-500 pb-2'>
												<div className='flex gap-2'>
													<div className='flex-shrink-0'>
														<Avatar
															src={activeMails[0]?.user.image?.thumb}
															className='!w-12'
															name={`${activeMails[0]?.user?.firstName} ${activeMails[0]?.user?.lastName}`}
														/>
													</div>
													<div className='grow'>
														<div className='flex text-lg font-semibold'>
															{`${activeMails[0]?.user?.firstName} ${activeMails[0]?.user?.lastName}`}
														</div>
														<div className='flex'>
															{activeMails[0].title}
														</div>
													</div>
												</div>
												<div className='text-zinc-500'>
													{activeMails[0].dateTime}
												</div>
											</div>
											<div className='flex'>
												<MailContentViewerPart
													content={activeMails[0].content}
												/>
											</div>
										</div>
									</CardBody>
								)}
								{activeMails.length === 0 && (
									<CardBody>
										<div className='flex h-full items-center justify-center'>
											<div className='flex text-xl text-zinc-500'>
												No Messages Selected
											</div>
										</div>
									</CardBody>
								)}
							</Card>
						</div>
					</div>
				</div>
				<div className='flex'>
					<div className='grid w-full grid-cols-12 gap-4'>
						<div className='col-span-12'>
							<Card>
								<CardFooter>
									<CardFooterChild />
									<CardFooterChild>
										<Button icon='HeroTrash' color='red' title='Delete'>
											Delete
										</Button>
									</CardFooterChild>
								</CardFooter>
							</Card>
						</div>
					</div>
				</div>
			</Container>
		</PageWrapper>
	);
};

export default MailJunkClient;
