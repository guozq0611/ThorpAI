'use client';

import React, { useState } from 'react';
import PageWrapper from '@/components/layouts/PageWrapper/PageWrapper';
import Container from '@/components/layouts/Container/Container';
import Subheader, {
	SubheaderLeft,
	SubheaderRight,
	SubheaderSeparator,
} from '@/components/layouts/Subheader/Subheader';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import { appPages } from '@/config/pages.config';
import { TMail } from '@/types/common/mail.type';
import usersDb from '@/mocks/db/users.db';
import { Descendant } from 'slate';
import { useRouter } from 'next/navigation';
import Card, { CardBody, CardFooter, CardFooterChild } from '@/components/ui/Card';
import MailSidebarItemPart from '@/app/[locale]/mail/_parts/MailSidebarItem.part';
import Avatar from '@/components/Avatar';
import MailContentViewerPart from '@/app/[locale]/mail/_parts/MailContentViewer.part';

const mails: TMail[] = [
	{
		id: 1,
		user: usersDb[1],
		fold: 'Inbox',
		isNew: true,
		dateTime: '09:18',
		title: 'Lorem ipsum dolor sit',
		content: JSON.parse(
			'[{"type": "paragraph","children": [{"text": "Hello,"}]}, {"type": "paragraph","children": [{"text": "Nullam laoreet quis orci vitae ornare. Praesent imperdiet magna orci, eu pharetra diam cursus a. Cras eleifend consequat nulla. Aliquam lacinia erat ac odio sodales fermentum. Etiam vehicula nisl sit amet elementum imperdiet. Sed porta elementum luctus. Suspendisse venenatis odio ligula, eget scelerisque eros vehicula fringilla. Maecenas vehicula cursus nibh, eu finibus nunc pretium vel. Curabitur ut tincidunt velit. Praesent at malesuada quam."}]}, {"type": "paragraph","children": [{"text": "Mauris at imperdiet dui, eu porta lacus. Aenean non sapien dolor. Curabitur placerat metus dui, ut iaculis leo feugiat sed. Curabitur dapibus commodo felis. Proin sit amet orci sagittis, pretium felis eget, elementum sapien. Suspendisse ut enim ligula. Vestibulum ut sapien vitae nisl facilisis laoreet. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Fusce a auctor risus. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Morbi at dapibus metus, eget dictum tellus. Etiam pharetra tincidunt placerat."}]}, {"type": "paragraph","children": [{"text": "Proin eget tellus condimentum, bibendum enim eu, auctor nisi. Quisque mauris sapien, rhoncus vitae sem in, sagittis consequat erat. Praesent varius erat vitae elit sodales ornare. Quisque consequat nisl at elementum porttitor. Nullam aliquet leo in tortor convallis, at suscipit purus tincidunt. Morbi tincidunt augue vel lacus semper, nec tempus erat mattis. Fusce malesuada magna non mauris porta, eu lobortis arcu pellentesque. Vivamus ut faucibus sapien. Nunc maximus sagittis sem. Aliquam sit amet risus nec enim vehicula pulvinar sit amet porttitor ligula."}]}, {"type": "paragraph","children": [{"text": "Regards."}]}]',
		) as Descendant[],
		attachment: ['../', '../'],
		flag: true,
	},
	{
		id: 2,
		user: usersDb[2],
		fold: 'Inbox',
		isNew: true,
		dateTime: '08:32',
		title: 'Lorem ipsum dolor sit',
		content: JSON.parse(
			'[{"type": "paragraph","children": [{"text": "Hi Team,"}]}, {"type":"paragraph","children":[{"text":"Praesent suscipit augue at dictum fermentum. Proin pulvinar luctus varius. Sed ullamcorper pharetra elit, non ultrices mauris euismod vel. Donec ligula tortor, molestie vel finibus ac, aliquet et nisl. Sed eget euismod ipsum, a tincidunt sapien. Suspendisse blandit est pretium urna maximus molestie. Nulla quis nisl metus. Nulla ac nulla non tortor viverra elementum. Maecenas posuere augue in ex elementum, eu eleifend turpis vestibulum. Maecenas ac dui a ex vestibulum mollis ac eu tellus. Curabitur accumsan varius massa eu finibus. Phasellus facilisis tincidunt ultricies. Aliquam condimentum efficitur tortor in placerat."}]}]',
		) as Descendant[],
	},
	{
		id: 3,
		user: usersDb[3],
		fold: 'Inbox',
		isNew: true,
		dateTime: '03:45',
		title: 'Lorem ipsum dolor sit',
		content: JSON.parse(
			'[{"type": "paragraph","children": [{"text": "Hi 👋,"}]}, {"type":"paragraph","children":[{"text":"Nunc nec lacus iaculis nulla condimentum scelerisque in id eros. Nulla facilisi. Fusce ut imperdiet nisi, sit amet gravida purus. Integer blandit sed purus et eleifend. Praesent erat orci, fringilla quis sodales eget, pulvinar at odio. Duis vel arcu vulputate, ullamcorper dolor in, semper metus. Duis pellentesque, risus id posuere sodales, nibh erat accumsan purus, eget euismod libero augue at neque. Suspendisse potenti."}]}]',
		) as Descendant[],
	},
	{
		id: 4,
		user: usersDb[0],
		fold: 'Inbox',
		dateTime: '03:45',
		title: 'Lorem ipsum dolor sit',
		content: JSON.parse(
			'[{"type": "paragraph","children": [{"text": "Hello Scott,"}]}, {"type":"paragraph","children":[{"text":"Etiam eu enim at lectus varius lobortis. Aliquam in facilisis nunc. Sed sed ultricies nulla. Suspendisse faucibus viverra cursus. Donec eleifend justo elementum felis dapibus dignissim. Aliquam turpis ipsum, eleifend sed ante sit amet, faucibus varius eros. Praesent posuere metus velit, eu viverra dui interdum sed. Nulla ac laoreet ante. Suspendisse venenatis erat eget ex pulvinar dignissim. Phasellus tempor lacus vitae lectus euismod fermentum. Praesent id ullamcorper orci. Phasellus ac libero vel arcu porttitor pulvinar vel eu eros. Ut ultrices, ex non volutpat egestas, dui neque aliquet turpis, sed sagittis arcu ex id ex. In in leo congue, vestibulum urna ac, auctor diam. Pellentesque congue ex sit amet velit faucibus maximus."}]}]',
		) as Descendant[],
		attachment: ['../', '../'],
		flag: true,
	},
	{
		id: 5,
		user: usersDb[0],
		fold: 'Inbox',
		dateTime: '03:45',
		title: 'Lorem ipsum dolor sit',
		content: JSON.parse(
			'[{"type": "paragraph","children": [{"text": "Hello,"}]},{"type":"paragraph","children":[{"text":"Aliquam non auctor tellus. Nullam sagittis urna a velit pellentesque, vitae rutrum enim fringilla. Nullam non tellus posuere, accumsan enim quis, finibus velit. Phasellus porttitor, urna id semper hendrerit, nisl turpis pretium quam, eu tincidunt dolor risus ac diam. Aliquam nec tortor ac massa viverra congue non et justo. Vestibulum et fringilla enim. Nulla sollicitudin purus nisl, ac efficitur nulla rhoncus ac. Proin condimentum ullamcorper nisl, ut congue magna tempor sed. Morbi est urna, dictum vel mollis et, interdum at ex. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Curabitur venenatis convallis leo, vel pharetra metus viverra nec. Suspendisse feugiat porta tempor. Aliquam accumsan, ex et placerat semper, turpis sem porttitor ligula, in porttitor erat urna ut erat. Integer faucibus velit id mauris lobortis, a mollis lectus rhoncus. Etiam placerat viverra justo, ac efficitur arcu pulvinar id. Donec lobortis eros vel vehicula hendrerit."}]}]',
		) as Descendant[],
		attachment: ['../', '../'],
	},
	{
		id: 6,
		user: usersDb[0],
		fold: 'Inbox',
		dateTime: '03:45',
		title: 'Lorem ipsum dolor sit',
		content: JSON.parse(
			'[{"type": "paragraph","children": [{"text": "Hello,"}]}, {"type":"paragraph","children":[{"text":"Morbi a tellus nec metus placerat mollis ac vitae mi. Cras condimentum ultricies massa sit amet placerat. Vivamus lectus neque, sagittis at volutpat nec, ullamcorper sed mauris. Maecenas fringilla non turpis pellentesque molestie. Donec nulla tortor, imperdiet ac risus sit amet, dapibus scelerisque nibh. Integer id laoreet sem, sit amet tristique elit. Duis mattis ligula viverra scelerisque iaculis. Aliquam eleifend euismod turpis sed ornare. Cras euismod risus ipsum. Vestibulum sit amet ipsum et nisl ultricies efficitur sit amet eu tellus. Sed purus risus, porta sit amet pulvinar id, pretium vitae massa. Proin condimentum mauris eget lobortis porta."}]}]',
		) as Descendant[],
	},
	{
		id: 7,
		user: usersDb[0],
		fold: 'Inbox',
		dateTime: '03:45',
		title: 'Lorem ipsum dolor sit',
		content: JSON.parse(
			'[{"type": "paragraph","children": [{"text": "Hello,"}]}, {"type":"paragraph","children":[{"text":"Duis tristique dictum purus, placerat tincidunt arcu consectetur sit amet. Suspendisse quis mauris sodales, cursus augue vitae, fringilla tortor. Mauris massa risus, fringilla volutpat justo eget, efficitur vulputate purus. Etiam vel tellus imperdiet, fringilla diam quis, iaculis diam. Nullam leo ipsum, efficitur eu porta quis, iaculis ut arcu. Aenean at efficitur erat, vitae volutpat arcu. Vivamus a dolor facilisis, lacinia ligula auctor, bibendum nisl. Quisque scelerisque tortor id porttitor molestie. Etiam dapibus lobortis justo, lobortis finibus eros malesuada non. Donec quis pharetra velit, in vehicula felis. Maecenas diam purus, auctor ac scelerisque non, luctus non sapien. Pellentesque faucibus ac dolor vel ullamcorper."}]}]',
		) as Descendant[],
	},
	{
		id: 8,
		user: usersDb[0],
		fold: 'Inbox',
		dateTime: '03:45',
		title: 'Lorem ipsum dolor sit',
		content: JSON.parse(
			'[{"type": "paragraph","children": [{"text": "Hello,"}]}, {"type":"paragraph","children":[{"text":"Aenean vitae justo nec purus varius rutrum sit amet vitae nisl. Nam maximus eget massa eu congue. Proin eget nulla risus. Nunc pulvinar ex vitae erat porttitor fringilla. Vivamus malesuada nulla ex, ut tincidunt lorem efficitur eget. Maecenas in dolor mi. Cras condimentum viverra dapibus. Nam accumsan leo vel dui molestie placerat. Aliquam tincidunt sapien ut neque varius vehicula. Maecenas vel laoreet tellus. Nullam pharetra tristique quam. Nunc eu magna erat. Praesent ante ipsum, tincidunt ut posuere tincidunt, vestibulum a nunc."}]}]',
		) as Descendant[],
	},
	{
		id: 9,
		user: usersDb[0],
		fold: 'Inbox',
		dateTime: '03:45',
		title: 'Lorem ipsum dolor sit',
		content: JSON.parse(
			'[{"type": "paragraph","children": [{"text": "Hello,"}]}, {"type":"paragraph","children":[{"text":"Praesent consectetur tincidunt velit. Curabitur est dui, viverra porta nisl eget, tincidunt ultricies lorem. Curabitur in pretium tellus, euismod varius turpis. Pellentesque luctus id sapien nec consequat. Fusce vehicula sapien odio, sit amet gravida ex semper non. Proin ornare diam ex, eget iaculis neque laoreet a. Suspendisse at metus quam. Nunc nec augue ultricies, dapibus nibh mattis, eleifend risus. Maecenas neque ex, elementum quis faucibus at, consectetur ut odio. Morbi vitae nunc sapien. In eu enim neque. Etiam orci sapien, consectetur sed risus eget, condimentum bibendum mauris. Cras nunc quam, venenatis id turpis sed, dignissim dictum lacus. Fusce gravida viverra urna sed mollis. Interdum et malesuada fames ac ante ipsum primis in faucibus. Sed nec scelerisque libero."}]}]',
		) as Descendant[],
		attachment: ['../', '../'],
	},
	{
		id: 10,
		user: usersDb[0],
		fold: 'Inbox',
		dateTime: '03:45',
		title: 'Lorem ipsum dolor sit',
		content: JSON.parse(
			'[{"type": "paragraph","children": [{"text": "Hello,"}]}, {"type":"paragraph","children":[{"text":"Cras turpis erat, malesuada a vestibulum et, efficitur non eros. Cras facilisis leo quis interdum gravida. Sed vel imperdiet nisl. Sed hendrerit, massa quis pellentesque vestibulum, felis quam varius libero, eget finibus ante purus et arcu. Suspendisse hendrerit sapien at sodales mollis. Aliquam leo metus, blandit eget ultricies luctus, tempor in lacus. Donec eget ullamcorper elit. Fusce cursus, neque nec dignissim sollicitudin, nulla risus gravida mauris, ut pulvinar velit diam at orci. Sed a placerat ex. Integer vestibulum orci nulla, quis varius mauris convallis in. Sed efficitur tempor augue, a iaculis mauris."}]}]',
		) as Descendant[],
	},
	{
		id: 11,
		user: usersDb[0],
		fold: 'Inbox',
		dateTime: '03:45',
		title: 'Lorem ipsum dolor sit',
		content: JSON.parse(
			'[{"type": "paragraph","children": [{"text": "Hello,"}]}, {"type":"paragraph","children":[{"text":"In mauris nisl, tempus vel ipsum vitae, sagittis vestibulum ex. Nam aliquet mauris eget dui dictum pellentesque. Quisque nec dolor hendrerit, scelerisque magna in, sagittis turpis. Donec quis orci in sem vestibulum consequat. Aenean dolor sem, euismod sit amet magna eu, sagittis facilisis mauris. Nulla laoreet tincidunt risus nec finibus. In tempor sollicitudin sem. Fusce commodo diam mi, ut porttitor nisi ultricies a. Vivamus vel sodales urna. Donec at hendrerit erat, id tincidunt diam. Sed in ligula accumsan, tincidunt massa quis, auctor est. Quisque at lorem euismod sem suscipit maximus. Praesent mollis fermentum turpis in rutrum."}]}]',
		) as Descendant[],
	},
	{
		id: 12,
		user: usersDb[0],
		fold: 'Inbox',
		dateTime: '03:45',
		title: 'Lorem ipsum dolor sit',
		content: JSON.parse(
			'[{"type": "paragraph","children": [{"text": "Hello,"}]}, {"type":"paragraph","children":[{"text":"Nam scelerisque arcu id diam sodales egestas. Maecenas molestie neque vel magna malesuada, sit amet semper sapien sollicitudin. Pellentesque porttitor hendrerit arcu vitae ullamcorper. Vestibulum eu ipsum venenatis, sodales ligula quis, pretium ex. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras faucibus ut magna quis sagittis. Maecenas eget ultricies augue, eu vulputate est. Vivamus dictum nunc at consectetur efficitur. Pellentesque gravida sapien ligula. Morbi tempor blandit viverra."}]}]',
		) as Descendant[],
	},
];

const MailInboxClient = () => {
	const [activeItem, setActiveItem] = useState<number[]>([mails[0].id]);

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
							</Card>
						</div>
					</div>
				</div>
				<div className='flex'>
					<div className='grid w-full grid-cols-12 gap-4'>
						<div className='col-span-12'>
							<Card>
								<CardFooter>
									<CardFooterChild>
										<Button
											icon='HeroArrowUturnLeft'
											title='Reply'
											color='emerald'
											className='!px-0'>
											Reply
										</Button>
										<Button
											icon='HeroArrowUturnRight'
											title='Forward'
											color='amber'
											className='!px-0'>
											Forward
										</Button>
									</CardFooterChild>
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

export default MailInboxClient;
