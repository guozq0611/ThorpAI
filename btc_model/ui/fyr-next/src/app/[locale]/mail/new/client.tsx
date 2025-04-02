'use client';

import React, { KeyboardEventHandler, useEffect, useState } from 'react';
import { useFormik } from 'formik';
import { Descendant } from 'slate';
import PageWrapper from '@/components/layouts/PageWrapper/PageWrapper';
import Subheader, {
	SubheaderLeft,
	SubheaderRight,
	SubheaderSeparator,
} from '@/components/layouts/Subheader/Subheader';
import { appPages } from '@/config/pages.config';
import Button from '@/components/ui/Button';
import Container from '@/components/layouts/Container/Container';
import Card, { CardBody, CardFooter, CardFooterChild } from '@/components/ui/Card';
import Label from '@/components/form/Label';
import SelectReact from '@/components/form/SelectReact';
import RichText from '@/components/RichText';
import Link from 'next/link';

interface Option {
	readonly label: string;
	readonly value: string;
}

const createOption = (label: string) => ({
	label,
	value: label,
});

const NewMailClient = () => {
	const formik = useFormik({
		initialValues: {
			to: [
				{ label: 'john@omtanke.studio', value: 'john@omtanke.studio' },
				{ label: 'scott@omtanke.studio', value: 'scott@omtanke.studio' },
			],
			cc: [],
			bcc: [],
			description: JSON.parse(
				'[{"type":"paragraph","children":[{"text":"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam malesuada nisl sed metus maximus imperdiet. Aenean tortor mi, pretium et faucibus elementum, pulvinar ultricies ex. Vivamus pharetra dui interdum, semper diam eget, blandit urna. Etiam eu tristique leo. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. In eros mi, vehicula sed ex sed, accumsan posuere leo. Vestibulum auctor aliquam elit, ut maximus felis gravida in. Donec feugiat sit amet est egestas porttitor. Suspendisse egestas nisi nec urna consequat, quis lobortis elit interdum. Pellentesque purus nibh, dignissim porta tincidunt id, convallis id lectus. In varius ipsum non turpis suscipit, ac ultrices nisi congue. Phasellus eget lectus eget dui sodales sollicitudin ut a nisi."}]}]',
			) as Descendant[],
		},
		onSubmit: (values) => {
			console.log(values);
		},
	});

	const [inputValueTo, setInputValueTo] = React.useState('');
	const [valueTo, setValueTo] = React.useState<readonly Option[]>(formik.values.to);
	const handleKeyDownTo: KeyboardEventHandler = (event) => {
		if (!inputValueTo) return;
		switch (event.key) {
			case 'Enter':
			case 'Tab':
				setValueTo((prev) => [...prev, createOption(inputValueTo)]);
				setInputValueTo('');
				event.preventDefault();
				break;
			default:
		}
	};
	useEffect(() => {
		void formik.setFieldValue('to', valueTo);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [valueTo]);

	const [inputValueCc, setInputValueCc] = useState('');
	const [valueCc, setValueCc] = useState<readonly Option[]>(formik.values.cc);
	const handleKeyDownCc: KeyboardEventHandler = (event) => {
		if (!inputValueCc) return;
		switch (event.key) {
			case 'Enter':
			case 'Tab':
				setValueCc((prev) => [...prev, createOption(inputValueCc)]);
				setInputValueCc('');
				event.preventDefault();
				break;
			default:
		}
	};
	useEffect(() => {
		void formik.setFieldValue('cc', valueCc);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [valueCc]);

	const [inputValueBcc, setInputValueBcc] = useState('');
	const [valueBcc, setValueBcc] = useState<readonly Option[]>(formik.values.bcc);
	const handleKeyDownBcc: KeyboardEventHandler = (event) => {
		if (!inputValueBcc) return;
		switch (event.key) {
			case 'Enter':
			case 'Tab':
				setValueBcc((prev) => [...prev, createOption(inputValueBcc)]);
				setInputValueBcc('');
				event.preventDefault();
				break;
			default:
		}
	};
	useEffect(() => {
		void formik.setFieldValue('Bcc', valueBcc);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [valueBcc]);

	return (
		<PageWrapper>
			<Subheader>
				<SubheaderLeft>
					<Link href={`../${appPages.mailAppPages.subPages.inboxPages.to}`}>
						<Button icon='HeroArrowLeft' className='!px-0'>
							Back to List
						</Button>
					</Link>
					<SubheaderSeparator />
				</SubheaderLeft>
				<SubheaderRight>
					<Button icon='HeroPaperAirplane' title='Send Mail' variant='solid'>
						Send
					</Button>
				</SubheaderRight>
			</Subheader>
			<Container className='flex shrink-0 grow basis-auto flex-col gap-4 pb-0'>
				<div className='flex h-full flex-wrap content-start'>
					<div className='mb-4 grid h-full w-full grid-cols-12 gap-4'>
						<div className='col-span-12 flex h-full flex-col gap-4'>
							<Card className='h-full'>
								<CardBody>
									<div className='grid grid-cols-12 gap-4'>
										<div className='col-span-12'>
											<div className='flex items-center gap-4'>
												<div className='shrink-0'>
													<Label htmlFor='to'>To:</Label>
												</div>
												<div className='grow'>
													<SelectReact
														isCreatable
														inputValue={inputValueTo}
														isClearable
														isMulti
														menuIsOpen={false}
														onChange={(newValue) =>
															// @ts-ignore
															setValueTo(newValue)
														}
														onInputChange={(newValue) =>
															setInputValueTo(newValue)
														}
														onKeyDown={handleKeyDownTo}
														placeholder='Email address ...'
														value={valueTo}
														name='to'
													/>
												</div>
											</div>
										</div>
										<div className='col-span-12'>
											<div className='flex items-center gap-4'>
												<div className='shrink-0'>
													<Label htmlFor='cc'>Cc:</Label>
												</div>
												<div className='grow'>
													<SelectReact
														isCreatable
														inputValue={inputValueCc}
														isClearable
														isMulti
														menuIsOpen={false}
														onChange={(newValueCc) =>
															// @ts-ignore
															setValueCc(newValueCc)
														}
														onInputChange={(newValueCc) =>
															setInputValueCc(newValueCc)
														}
														onKeyDown={handleKeyDownCc}
														placeholder='Email address ...'
														value={valueCc}
														name='cc'
													/>
												</div>
											</div>
										</div>
										<div className='col-span-12'>
											<div className='flex items-center gap-4'>
												<div className='shrink-0'>
													<Label htmlFor='bcc'>Bcc:</Label>
												</div>
												<div className='grow'>
													<SelectReact
														isCreatable
														inputValue={inputValueBcc}
														isClearable
														isMulti
														menuIsOpen={false}
														onChange={(newValueBcc) =>
															// @ts-ignore
															setValueCc(newValueBcc)
														}
														onInputChange={(newValueBcc) =>
															setInputValueBcc(newValueBcc)
														}
														onKeyDown={handleKeyDownBcc}
														placeholder='Email address ...'
														value={valueBcc}
														name='bcc'
													/>
												</div>
											</div>
										</div>
										<div className='col-span-12'>
											<RichText
												id='description'
												value={formik.values.description}
												handleChange={(event) => {
													formik
														.setFieldValue('description', event)
														.then(() => {})
														.catch(() => {});
												}}
											/>
										</div>
									</div>
								</CardBody>
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
											icon='HeroXCircle'
											title='Forward'
											color='red'
											className='!px-0'>
											Cancel
										</Button>
										<Button
											icon='HeroBookmarkSquare'
											title='Reply'
											color='amber'
											className='!px-0'>
											Save Draft
										</Button>
									</CardFooterChild>
									<CardFooterChild>
										<Button
											icon='HeroPaperAirplane'
											title='Send Mail'
											variant='solid'>
											Send
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

export default NewMailClient;
